import re
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Callable, Tuple
from django.utils import timezone
from users.models_profile import TherapistProfile, LicenseVerificationLog

@dataclass
class LicenseCheckResult:
    status: str  # one of TherapistProfile.LICENSE_STATUS_CHOICES keys
    message: str = ""
    source_url: str = ""
    raw: Optional[dict] = None

# Strategy registry: state -> callable(profile) -> LicenseCheckResult
STATE_STRATEGIES: Dict[str, Callable[[TherapistProfile], LicenseCheckResult]] = {}

def register_state(state: str):
    def deco(fn):
        STATE_STRATEGIES[state.upper()] = fn
        return fn
    return deco

# Example placeholder strategy for CA (California) using hypothetical endpoint
@register_state('CA')
def verify_ca(profile: TherapistProfile) -> LicenseCheckResult:
    # Placeholder: real CA BBS/BOP boards differ per license type.
    # This just demonstrates structure; returns unverified so we don't falsely approve.
    return LicenseCheckResult(status='unverified', message='CA verification not yet implemented')

@register_state('KY')
def verify_ky(profile: TherapistProfile) -> LicenseCheckResult:
    """Perform Kentucky OOP WebForms search and parse result row.

    Steps:
      1. GET landing page to capture __VIEWSTATE / __EVENTVALIDATION / __VIEWSTATEGENERATOR.
      2. POST form with radio selection (individual), license number (or name fallback), and Search button.
      3. Parse returned HTML segment #ContentPlaceHolder2_LData for result table.
      4. Extract row matching license number (preferred) else name; capture board, license type, issue & expiration dates, discipline flag, status.
      5. Map to internal status.

    Limitations: If site structure changes or additional anti-bot measures appear, this may fail and fall back gracefully.
    We intentionally do not select all boards explicitly (site auto-loads board list); targeting by license number is usually unique.
    """
    import bs4
    base = "https://oop.ky.gov"
    lnum = (profile.license_number or '').strip()
    # Prefer explicitly entered licensed name fields over profile name
    lname = (profile.license_last_name or profile.last_name or '').strip()
    fname = (profile.license_first_name or profile.first_name or '').strip()
    if not lnum and not (lname or fname):
        return LicenseCheckResult(status='error', message='Missing license number or licensed name', source_url=base)
    try:
        session = requests.Session()
        landing = session.get(base, timeout=15)
    except Exception as ex:
        return LicenseCheckResult(status='error', message=f'KY portal unreachable: {ex.__class__.__name__}', source_url=base)
    if landing.status_code != 200:
        return LicenseCheckResult(status='error', message=f'KY portal HTTP {landing.status_code}', source_url=base, raw={'status_code': landing.status_code})
    soup = bs4.BeautifulSoup(landing.text, 'html.parser')
    def grab(name):
        el = soup.find('input', {'name': name})
        return el.get('value') if el else ''
    viewstate = grab('__VIEWSTATE')
    eventval = grab('__EVENTVALIDATION')
    viewstategen_el = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
    viewstategen = viewstategen_el.get('value') if viewstategen_el else ''
    # Build POST data
    data = {
        '__VIEWSTATE': viewstate,
        '__EVENTVALIDATION': eventval,
        '__VIEWSTATEGENERATOR': viewstategen,
        'ctl00$ContentPlaceHolder2$rdLictype': '1',  # Individual
        'ctl00$ContentPlaceHolder2$TLicno': lnum,
        # Always include provided licensed first/last name (site should ignore if license number sufficient)
        'ctl00$ContentPlaceHolder2$TFname': fname,
        'ctl00$ContentPlaceHolder2$TLname': lname,
        'ctl00$ContentPlaceHolder2$DStatus': '',
        'ctl00$ContentPlaceHolder2$BSrch': 'Search',
    }
    try:
        resp = session.post(base, data=data, timeout=20)
    except Exception as ex:
        return LicenseCheckResult(status='error', message=f'KY search failed: {ex.__class__.__name__}', source_url=base)
    if resp.status_code != 200:
        return LicenseCheckResult(status='error', message=f'KY search HTTP {resp.status_code}', source_url=base, raw={'status_code': resp.status_code})
    rsoup = bs4.BeautifulSoup(resp.text, 'html.parser')
    container = rsoup.find(id='ContentPlaceHolder2_LData')
    if not container:
        return LicenseCheckResult(status='error', message='KY result container missing', source_url=base)
    # Find table rows after header; header contains <B>Name</B>
    rows = container.find_all('tr')
    target = None
    header_seen = False
    for tr in rows:
        cells = [c.get_text(strip=True) for c in tr.find_all('td')]
        if not cells:
            continue
        if any('Name' == c for c in cells) and any('License Number' in c for c in cells):
            header_seen = True
            continue
        if header_seen and len(cells) >= 9:
            # cells mapping based on sample: 0 Name,1 Board,2 License Type,3 Legacy,4 License Number,5 Disciplinary Actions,6 Status,7 Issue,8 Expiration
            lic_no = cells[4]
            name_cell = cells[0]
            if lnum and lic_no == lnum:
                target = cells; break
            if not lnum:
                # Attempt stricter match using both names if available
                if lname and fname:
                    if lname.lower() in name_cell.lower() and fname.lower() in name_cell.lower():
                        target = cells; break
                elif lname and lname.lower() in name_cell.lower():
                    target = cells; break
                elif fname and fname.lower() in name_cell.lower():
                    target = cells; break
    if not target:
        # Check for total matches indicator = 0
        if 'Total Matches Found : 0' in container.get_text():
            return LicenseCheckResult(status='not_found', message='No KY matches', source_url=base)
        return LicenseCheckResult(status='unverified', message='KY match not isolated', source_url=base)
    name, board, lic_type, legacy_no, lic_no, disciplinary, status_text, issue_date, exp_date = target[:9]
    # Expected names (override > profile); require BOTH first & last to appear in returned name for a pass.
    expected_fn = (profile.license_first_name or profile.first_name or '').strip().lower()
    expected_ln = (profile.license_last_name or profile.last_name or '').strip().lower()
    name_lc = name.lower()
    name_match = True
    if expected_fn and expected_ln:
        name_match = expected_fn in name_lc and expected_ln in name_lc
    elif expected_fn or expected_ln:
        # If only one provided still require it present
        solo = expected_fn or expected_ln
        name_match = solo in name_lc

    # License number already matched to select target row (lic_no == lnum if lnum provided)
    license_match = True
    if lnum:
        license_match = (lic_no == lnum)

    # Status must equal 'Active' exactly (case-insensitive stripping)
    status_clean = status_text.strip().lower()
    status_is_active = (status_clean == 'active')

    # Disciplinary must be 'No' (case-insensitive) OR blank
    disciplinary_clean = disciplinary.strip().lower()
    disciplinary_clear = (disciplinary_clean == '' or disciplinary_clean == 'no')

    # Loose License Type matching: attempt to confirm scraped lic_type aligns with stored profile license_type (if any)
    license_type_loose_match = True
    profile_license_obj = getattr(profile, 'license_type', None)
    if profile_license_obj and lic_type:
        expected_variants = set()
        try:
            if profile_license_obj.name:
                expected_variants.add(profile_license_obj.name.strip())
        except Exception:
            pass
        short_desc = getattr(profile_license_obj, 'short_description', '') or ''
        if short_desc:
            expected_variants.add(short_desc.strip())
        # Tokenize and remove generic words for comparison; also map common abbreviations
        stopwords = {'license','licensed','of','and','the','state','board','therapy','therapist','professional','clinical'}
        alias_groups = [
            {'lcsw','licensed clinical social worker','clinical social worker','social worker'},
            {'lpcc','licensed professional clinical counselor','professional clinical counselor','clinical counselor','counselor'},
            {'lpc','licensed professional counselor','professional counselor','counselor'},
            {'lmft','licensed marriage and family therapist','marriage and family therapist','mft'},
            {'psychologist','psychology','psychologist license'},
        ]
        def tokens(s: str):
            s = s.lower()
            s = re.sub(r'[\/,&()-]+', ' ', s)
            s = re.sub(r'\s+', ' ', s).strip()
            return {t for t in s.split(' ') if t and t not in stopwords}
        lic_tokens = tokens(lic_type)
        expected_token_sets = [tokens(v) for v in expected_variants if v]
        direct_overlap = any(lic_tokens & ets for ets in expected_token_sets)
        def alias_overlap():
            for group in alias_groups:
                if group & lic_tokens:
                    for ets in expected_token_sets:
                        if group & ets:
                            return True
            return False
        license_type_loose_match = direct_overlap or alias_overlap()

    # Expiration must be on or after today.
    # KY format observed: MM/DD/YYYY. We support fallback to legacy MM/YYYY if site changes back.
    exp_valid_format = False
    exp_on_or_after_today = False
    import datetime
    now = datetime.date.today()
    exp_clean = exp_date.strip()
    m_full = re.match(r'^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(\d{4})$', exp_clean)
    if m_full:
        exp_valid_format = True
        mm = int(m_full.group(1)); dd = int(m_full.group(2)); yy = int(m_full.group(3))
        try:
            exp_dt = datetime.date(yy, mm, dd)
            exp_on_or_after_today = exp_dt >= now
        except ValueError:
            # Invalid calendar date (e.g., Feb 30) -> format invalid
            exp_valid_format = False
    else:
        # Fallback MM/YYYY (legacy) interpret as last day of month
        m_short = re.match(r'^(0?[1-9]|1[0-2])/(\d{4})$', exp_clean)
        if m_short:
            exp_valid_format = True
            mm = int(m_short.group(1)); yy = int(m_short.group(2))
            # Compute last day of month
            if mm == 12:
                last_day = 31
            else:
                first_next = datetime.date(yy + (1 if mm==12 else 0), (1 if mm==12 else mm+1), 1)
                last_day = (first_next - datetime.timedelta(days=1)).day
            exp_dt = datetime.date(yy, mm, last_day)
            exp_on_or_after_today = exp_dt >= now
    # Determine internal status based on failing rules precedence
    failure_reason = None
    internal = 'unverified'
    if not name_match or not license_match:
        failure_reason = 'name/license mismatch'
        internal = 'unverified'
    elif not license_type_loose_match:
        failure_reason = 'license type mismatch'
        internal = 'unverified'
    elif not status_is_active:
        failure_reason = 'status not active'
        internal = 'unverified'
    elif not disciplinary_clear:
        failure_reason = 'disciplinary flag'
        internal = 'disciplinary_flag'
    elif not exp_valid_format:
        failure_reason = 'invalid expiration format'
        internal = 'unverified'
    elif not exp_on_or_after_today:
        failure_reason = 'expired'
        internal = 'expired'
    else:
        internal = 'active_good_standing'

    raw = {
        'name': name,
        'board': board,
        'license_type': lic_type,
        'legacy_number': legacy_no,
        'license_number': lic_no,
        'disciplinary_actions': disciplinary,
        'status_text': status_text,
        'issue_date': issue_date,
        'expiration_date': exp_date,
        'source': 'KY_OOP',
        'criteria': {
            'name_match': name_match,
            'license_match': license_match,
            'status_is_active': status_is_active,
            'disciplinary_clear': disciplinary_clear,
            'license_type_loose_match': license_type_loose_match,
            'expiration_format_valid': exp_valid_format,
            'expiration_on_or_after_today': exp_on_or_after_today,
        },
        'failure_reason': failure_reason,
    }
    if internal == 'active_good_standing':
        msg = f"KY: Active (exp {exp_date})"
    else:
        # Provide concise message incl reason
        if failure_reason == 'expired':
            msg = f"KY: Expired (exp {exp_date})"
        elif failure_reason == 'disciplinary flag':
            msg = f"KY: Disciplinary flag"
        elif failure_reason == 'status not active':
            msg = f"KY: Status '{status_text}' not Active"
        elif failure_reason == 'name/license mismatch':
            msg = "KY: Name/license mismatch"
        elif failure_reason == 'license type mismatch':
            msg = "KY: License type mismatch"
        elif failure_reason == 'invalid expiration format':
            msg = f"KY: Invalid expiration '{exp_date}'"
        else:
            msg = f"KY: Unverified"
    return LicenseCheckResult(status=internal, message=msg, source_url=base, raw=raw)

# Fallback generic strategy (HTML scraping patterns could go here)

def run_license_verification(profile: TherapistProfile) -> LicenseCheckResult:
    state = (profile.license_state or '').upper().strip()
    if not state or not profile.license_number:
        return LicenseCheckResult(status='error', message='Missing state or license number')
    strat = STATE_STRATEGIES.get(state)
    if not strat:
        return LicenseCheckResult(status='unverified', message=f'No automated verifier for {state}')
    try:
        return strat(profile)
    except Exception as ex:
        return LicenseCheckResult(status='error', message=str(ex)[:240])


def verify_and_persist(profile: TherapistProfile) -> LicenseCheckResult:
    result = run_license_verification(profile)
    # If strategy didn't set a source URL, attempt to pull from StateLicenseBoard config
    if not result.source_url:
        try:
            from users.models_profile import StateLicenseBoard
            boards = StateLicenseBoard.objects.filter(state__iexact=profile.license_state, active=True)
            # Prefer matching license_type if present
            if profile.license_type:
                board = boards.filter(license_type__iexact=profile.license_type.name).first() or boards.filter(license_type='').first()
            else:
                board = boards.filter(license_type='').first() or boards.first()
            if board:
                result.source_url = board.search_url
        except Exception:
            pass
    profile.license_status = result.status
    profile.license_last_verified_at = timezone.now()
    if result.source_url:
        profile.license_verification_source_url = result.source_url[:512]
    if result.raw:
        profile.license_verification_raw = result.raw
    profile.save(update_fields=['license_status','license_last_verified_at','license_verification_source_url','license_verification_raw'])
    LicenseVerificationLog.objects.create(
        therapist=profile,
        status=result.status,
        message=result.message[:512],
        raw=result.raw or {}
    )
    return result
