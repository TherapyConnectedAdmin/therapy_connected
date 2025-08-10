from users.models_profile import ZipCode
from users.location_utils import ensure_zipcode
from threading import Lock
import time

_ZIP_META_CACHE = {}
_ZIP_META_CACHE_LOCK = Lock()
_ZIP_META_TTL_SECONDS = 60 * 60 * 24  # 24h

def _resolve_zip(user_zip: str):
    if not user_zip:
        return None, None
    z5 = user_zip[:5]
    now = time.time()
    with _ZIP_META_CACHE_LOCK:
        cached = _ZIP_META_CACHE.get(z5)
        if cached and (now - cached[2] < _ZIP_META_TTL_SECONDS):
            return cached[0], cached[1]
    city = state = None
    # Query local table; dynamically enrich if missing
    try:
        row = ZipCode.objects.filter(pk=z5).only('city','state').first()
        if not row:
            row = ensure_zipcode(z5)
        if row:
            city, state = row.city, row.state
    except Exception:
        city = state = None
    with _ZIP_META_CACHE_LOCK:
        _ZIP_META_CACHE[z5] = (city, state, now)
    return city, state

def location_context(request):
    """Provide user zip and derived city/state to all templates (with caching)."""
    user_zip = request.session.get('user_zip')
    city = state = None
    if user_zip:
        city, state = _resolve_zip(user_zip)
    return {
        'user_zip': user_zip,
        'user_zip_city': city,
        'user_zip_state': state,
    }
