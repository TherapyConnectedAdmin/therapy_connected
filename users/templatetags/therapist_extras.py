
from django import template
from users.location_utils import get_primary_location as shared_get_primary_location

register = template.Library()


@register.filter
def get_primary_location(locations):
    """Return the primary location from a queryset of locations, or None if not found. Uses shared utility."""
    return shared_get_primary_location(locations)
