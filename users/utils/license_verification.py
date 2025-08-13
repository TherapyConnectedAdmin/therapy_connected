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
    lname = (profile.license_last_name or profile.last_name or '').strip()
    if not lnum and not lname:
        return LicenseCheckResult(status='error', message='Missing license number and last name', source_url=base)
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
        'ctl00$ContentPlaceHolder2$TFname': '',
        'ctl00$ContentPlaceHolder2$TLname': lname if not lnum else '',  # only use name if license number absent
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
            if not lnum and lname and lname.lower() in name_cell.lower():
                target = cells; break
    if not target:
        # Check for total matches indicator = 0
        if 'Total Matches Found : 0' in container.get_text():
            return LicenseCheckResult(status='not_found', message='No KY matches', source_url=base)
        return LicenseCheckResult(status='unverified', message='KY match not isolated', source_url=base)
    name, board, lic_type, legacy_no, lic_no, disciplinary, status_text, issue_date, exp_date = target[:9]
    # Determine internal status
    status_lc = status_text.lower()
    if 'expired' in status_lc:
        internal = 'expired'
    elif any(w in status_lc for w in ['suspend','revok','probation','surrender']):
        internal = 'disciplinary_flag'
    elif status_lc.startswith('active'):
        # Consider disciplinary column
        if disciplinary.lower() == 'no':
            internal = 'active_good_standing'
        else:
            internal = 'disciplinary_flag'
    else:
        internal = 'unverified'
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
    }
    msg = f"KY: {status_text} (exp {exp_date}) disciplinary={disciplinary}"
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
