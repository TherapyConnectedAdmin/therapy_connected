from uszipcode import SearchEngine
import time
from threading import Lock

# Simple in-memory cache for zip metadata to reduce repeated lookups per process.
# Structure: { zip: (city, state, timestamp) }
_ZIP_CACHE = {}
_ZIP_CACHE_LOCK = Lock()
_ZIP_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24h TTL

def _resolve_zip(user_zip: str):
    if not user_zip:
        return None, None
    now = time.time()
    # Try cache
    with _ZIP_CACHE_LOCK:
        cached = _ZIP_CACHE.get(user_zip)
        if cached and (now - cached[2] < _ZIP_CACHE_TTL_SECONDS):
            return cached[0], cached[1]
    city = state = None
    try:
        search = SearchEngine()
        zobj = search.by_zipcode(user_zip)
        if (not zobj or not getattr(zobj, 'lat', None)):
            try:
                search_full = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)
                zobj_full = search_full.by_zipcode(user_zip)
                if zobj_full:
                    zobj = zobj_full
            except Exception:
                pass
        if zobj:
            city = getattr(zobj, 'major_city', None) or getattr(zobj, 'post_office_city', None) or getattr(zobj, 'city', None)
            state = getattr(zobj, 'state', None)
    except Exception:
        city = state = None
    # Store in cache
    with _ZIP_CACHE_LOCK:
        _ZIP_CACHE[user_zip] = (city, state, now)
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
