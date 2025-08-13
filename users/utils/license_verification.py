import re
import requests
from dataclasses import dataclass
from typing import Optional, Dict, Callable
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
    """Attempt a lightweight verification against Kentucky OOP site (placeholder).

    The Kentucky Office of Occupations & Professions (oop.ky.gov) exposes search pages per board.
    Many boards use POST form submissions; without a formal API we perform a simple GET to the
    base site to ensure reachability and construct a suggested manual lookup URL recorded in logs.

    Future enhancement: implement board-specific scraping using requests + BeautifulSoup
    (ensure robots.txt compliance and add rate limiting & caching).
    """
    base = "https://oop.ky.gov"
    # Construct a human-review lookup hint using last name (fallback license number)
    lname = (profile.license_last_name or profile.last_name or '').strip()
    lnum = (profile.license_number or '').strip()
    # Placeholder heuristic URL (no guaranteed endpoint; serves as a starting point for staff)
    hint_url = base
    try:
        resp = requests.get(base, timeout=8)
        if resp.status_code == 200:
            # Do NOT assert active until real parsing implemented
            return LicenseCheckResult(status='unverified', message='KY site reachable – implement detailed scraping next', source_url=hint_url, raw={'status_code': resp.status_code})
        else:
            return LicenseCheckResult(status='error', message=f'KY site HTTP {resp.status_code}', source_url=hint_url, raw={'status_code': resp.status_code})
    except Exception as ex:
        return LicenseCheckResult(status='error', message=f'KY fetch failed: {ex.__class__.__name__}', source_url=hint_url)

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
