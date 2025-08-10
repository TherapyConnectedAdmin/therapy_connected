from users.models_profile import TherapistProfile, Location, ZipCode
from math import radians, sin, cos, atan2, sqrt
from typing import Optional

# Dynamic zipcode enrichment uses uszipcode if an unknown ZIP is requested.
try:
    from uszipcode import SearchEngine  # already in requirements
except Exception:  # pragma: no cover - defensive if library missing in some env
    SearchEngine = None

_ZIP_CACHE = {}

def get_zip_latlng(zip_code: str):
    if not zip_code:
        return None
    z5 = str(zip_code)[:5]
    if z5 in _ZIP_CACHE:
        return _ZIP_CACHE[z5]
    try:
        zobj = ZipCode.objects.filter(pk=z5).only('latitude','longitude').first()
        if zobj:
            _ZIP_CACHE[z5] = (float(zobj.latitude), float(zobj.longitude))
        else:
            _ZIP_CACHE[z5] = None
    except Exception:
        _ZIP_CACHE[z5] = None
    return _ZIP_CACHE[z5]

def ensure_zipcode(zip_code: str) -> Optional[ZipCode]:
    """Ensure a ZipCode row exists; if missing, attempt to fetch via uszipcode and insert.

    Returns the ZipCode instance or None if not resolvable.
    """
    if not zip_code:
        return None
    z5 = str(zip_code)[:5]
    existing = ZipCode.objects.filter(pk=z5).first()
    if existing:
        return existing
    # Attempt enrichment only if we have the uszipcode dataset available
    if SearchEngine is None:
        return None
    try:
        engine = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)
        rec = engine.by_zipcode(z5)
        if rec and rec.zipcode and rec.lat and rec.lng and rec.major_city and rec.state:
            try:
                created = ZipCode.objects.create(
                    zip=rec.zipcode,
                    city=str(rec.major_city).title(),
                    state=str(rec.state).upper(),
                    latitude=str(rec.lat),
                    longitude=str(rec.lng),
                )
                # prime cache
                _ZIP_CACHE[z5] = (float(created.latitude), float(created.longitude))
                return created
            except Exception:
                return ZipCode.objects.filter(pk=z5).first()
    except Exception:
        return None
    return None

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlmb/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def min_distance_between_zip_and_locations(user_zip: str, locations):
    user_ll = get_zip_latlng(user_zip)
    if not user_ll:
        return None
    min_d = None
    for loc in locations:
        ll = get_zip_latlng(getattr(loc,'zip',None))
        if not ll:
            continue
        d = haversine_miles(user_ll[0], user_ll[1], ll[0], ll[1])
        if min_d is None or d < min_d:
            min_d = d
    return round(min_d,1) if min_d is not None else None
# users/location_utils.py

def get_primary_location(locations_queryset):
    """
    Returns the primary location from a queryset of Location objects.
    If none is marked as primary, returns the first location or None.
    """
    if not locations_queryset:
        return None
    # If it's a queryset, evaluate it to a list
    locations = list(locations_queryset)
    if not locations:
        return None
    for loc in locations:
        if getattr(loc, 'is_primary', False):
            return loc
    return locations[0] if locations else None

def nearest_zip_from_coordinates(lat: float, lng: float) -> Optional[str]:
    """Find nearest stored ZipCode to provided lat/lng. If table is sparsely populated,
    this is a full scan; for large tables consider spatial indexing in future.
    """
    try:
        rows = list(ZipCode.objects.all().only('zip','latitude','longitude'))
        if not rows:
            return None
        best_zip = None
        best_d = None
        for r in rows:
            try:
                d = haversine_miles(float(lat), float(lng), float(r.latitude), float(r.longitude))
            except Exception:
                continue
            if best_d is None or d < best_d:
                best_d = d
                best_zip = r.zip
        return best_zip
    except Exception:
        return None
