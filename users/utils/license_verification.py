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
