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
