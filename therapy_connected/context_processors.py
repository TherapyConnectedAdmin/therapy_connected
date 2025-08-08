from uszipcode import SearchEngine

def location_context(request):
    """Provide user zip and derived city/state to all templates."""
    user_zip = request.session.get('user_zip')
    city = state = None
    if user_zip:
        try:
            # Simple lookup
            search = SearchEngine()
            zobj = search.by_zipcode(user_zip)
            if (not zobj or not getattr(zobj, 'lat', None)):
                # Comprehensive fallback
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
    return {
        'user_zip': user_zip,
        'user_zip_city': city,
        'user_zip_state': state,
    }
