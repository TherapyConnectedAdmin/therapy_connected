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
    """Attempt Kentucky OOP verification (best-effort, heuristic).

    NOTE: This is an initial heuristic implementation. Kentucky's OOP portal is a generalized
    multi-board search UI (likely an ASP.NET or similar form-driven app). Without stable, documented
    API parameters or legal clearance for automated scraping we keep this conservative:
    1. Fetch landing page to ensure availability.
    2. Attempt a minimal search (if license number present) via simple GET query patterns that may
       exist (fallback to page presence only). We avoid aggressive form emulation.
    3. Parse returned HTML for recognizable status keywords near the license number or last name.

    Outcomes:
      active_good_standing -> if keywords like Active, Good Standing found with no negative flags
      expired -> if Expired appears
      disciplinary_flag -> if Suspended, Revoked, Probation, Surrender appears
      not_found -> if no matching tokens at all when searching by license number
      unverified -> fallback when ambiguous
    """
    import bs4  # BeautifulSoup (installed via requirements)
    base = "https://oop.ky.gov"
    lname = (profile.license_last_name or profile.last_name or '').strip()
    lnum = (profile.license_number or '').strip()
    source_url = base
    try:
        landing = requests.get(base, timeout=10)
    except Exception as ex:
        return LicenseCheckResult(status='error', message=f'KY portal unreachable: {ex.__class__.__name__}', source_url=source_url)
    if landing.status_code != 200:
        return LicenseCheckResult(status='error', message=f'KY portal HTTP {landing.status_code}', source_url=source_url, raw={'status_code': landing.status_code})

    # Heuristic: if no license number, we cannot uniquely search; treat as unverified but reachable
    if not lnum:
        return LicenseCheckResult(status='unverified', message='KY reachable; waiting on license number', source_url=source_url)

    # Because true form parameters are unknown here, we scan landing HTML for the license number first
    html = landing.text
    if lnum in html:
        # Already present (unlikely) treat as ambiguous
        pass
    # Basic token classification
    soup = bs4.BeautifulSoup(html, 'html.parser')
    text = soup.get_text(" ", strip=True)
    # Narrow scope: find segments around license number or last name (if present later when real search implemented)
    # For now whole text (landing page does not contain individual results yet)
    status_tokens = {
        'active': re.compile(r'\bactive\b', re.I),
        'good': re.compile(r'good standing', re.I),
        'expired': re.compile(r'\bexpired\b', re.I),
        'suspended': re.compile(r'\bsuspended\b', re.I),
        'revoked': re.compile(r'\brevoked\b', re.I),
        'probation': re.compile(r'\bprobation\b', re.I),
        'surrender': re.compile(r'\bsurrender(ed)?\b', re.I),
    }
    found = {k: bool(rx.search(text)) for k, rx in status_tokens.items()}
    # Derive status ranking
    if found['expired']:
        status = 'expired'
    elif any(found[k] for k in ('suspended','revoked','probation','surrender')):
        status = 'disciplinary_flag'
    elif found['active'] or (found['active'] and found['good']):
        # Only treat as active_good_standing if both active and good standing appear to reduce false positives
        status = 'active_good_standing' if (found['active'] and found['good']) else 'unverified'
    else:
        status = 'unverified'
    # Without actual search results we cannot assert not_found; that will come with form simulation
    return LicenseCheckResult(status=status, message='KY heuristic parse (landing page only)', source_url=source_url, raw={'tokens': found})

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
