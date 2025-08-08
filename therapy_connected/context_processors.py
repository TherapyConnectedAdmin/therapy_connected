from uszipcode import SearchEngine

_search_engine = None

def _get_search():
    global _search_engine
    if _search_engine is None:
        try:
            _search_engine = SearchEngine(simple_zipcode=True)
        except Exception:
            _search_engine = None
    return _search_engine

def location_context(request):
    """Provide user zip and derived city/state to all templates."""
    user_zip = request.session.get('user_zip')
    city = state = None
    if user_zip:
        search = _get_search()
        try:
            if search:
                zobj = search.by_zipcode(user_zip)
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
