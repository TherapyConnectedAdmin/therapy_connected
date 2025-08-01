from django import template

register = template.Library()


def get_primary_location(locations):
    """
    Returns the primary location from a queryset or list of locations.
    Assumes the primary location is marked with is_primary_address=True, or returns the first if none marked.
    """
    if hasattr(locations, 'filter'):
        primary = locations.filter(is_primary_address=True).first()
        if primary:
            return primary
        return locations.first()
    # fallback for list
    for loc in locations:
        if getattr(loc, 'is_primary_address', False):
            return loc
    return locations[0] if locations else None

register.filter('get_primary_location', get_primary_location)
