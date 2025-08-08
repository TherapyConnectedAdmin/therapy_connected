from uszipcode import SearchEngine

_search_simple = None
_search_full = None

def _get_search_engines():
    """Lazily init simple + comprehensive search engines (API updated: no simple_zipcode kwarg)."""
    global _search_simple, _search_full
    if _search_simple is None:
        try:
            _search_simple = SearchEngine()
        except Exception:
            _search_simple = None
    if _search_full is None:
        try:
            _search_full = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)
        except Exception:
            _search_full = None
    return _search_simple, _search_full

def location_context(request):
    """Provide user zip and derived city/state to all templates."""
    user_zip = request.session.get('user_zip')
    city = state = None
    if user_zip:
        simple_engine, full_engine = _get_search_engines()
        try:
            zobj = None
            if simple_engine:
                zobj = simple_engine.by_zipcode(user_zip)
            if (not zobj or (not getattr(zobj, 'lat', None) and full_engine)) and full_engine:
                # Fallback to comprehensive if simple missing or incomplete
                zobj_full = full_engine.by_zipcode(user_zip)
                if zobj_full:
                    zobj = zobj_full
            if zobj:
                city = getattr(zobj, 'major_city', None) or getattr(zobj, 'post_office_city', None) or getattr(zobj, 'city', None)
                state = getattr(zobj, 'state', None)
        except Exception:
            pass
    return {
        'user_zip': user_zip,
        'user_zip_city': city,
        'user_zip_state': state,
    }
