from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

ESSENTIAL_FIELDS = [
    'profile_photo',
    'therapy_delivery_method',
    'license_type',
    # Newly counted basics for clearer early progress feedback
    'first_name',
    'last_name',
    'accepting_new_clients',  # tri-state string; blank means unset
    'intro_note',  # short intro blurb
    'personal_statement_01',  # detailed about me
]
# Relations that count toward essentials
RELATION_CHECKS = {
    'locations': lambda p: p.locations.exists(),
    'specialties': lambda p: p.specialties.exists(),
}

@dataclass
class CompletionResult:
    essential_total: int
    essential_filled: int
    percent: int
    details: Dict[str, bool]


def compute_profile_completion(profile) -> CompletionResult:
    details: Dict[str, bool] = {}
    # Direct fields
    for field in ESSENTIAL_FIELDS:
        val = getattr(profile, field, None)
        filled = bool(val)
        # ImageField returns FieldFile; treat existing name as filled
        if hasattr(val, 'name'):
            filled = bool(val.name)
        details[field] = filled
    # Relation checks
    for key, fn in RELATION_CHECKS.items():
        try:
            details[key] = bool(fn(profile))
        except Exception:
            details[key] = False
    essential_total = len(details)
    essential_filled = sum(1 for v in details.values() if v)
    percent = int((essential_filled / essential_total) * 100) if essential_total else 0
    return CompletionResult(essential_total, essential_filled, percent, details)
