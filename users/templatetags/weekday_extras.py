from django import template

register = template.Library()

WEEKDAY_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
WEEKDAY_LONG = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

@register.filter
def weekday_short(val):
    """Return 3-letter weekday name for integer 0-6; fallback to original value."""
    try:
        i = int(val)
    except (TypeError, ValueError):
        return val
    if 0 <= i < 7:
        return WEEKDAY_SHORT[i]
    return val

@register.filter
def weekday_long(val):
    """Return full weekday name for integer 0-6; fallback to original value."""
    try:
        i = int(val)
    except (TypeError, ValueError):
        return val
    if 0 <= i < 7:
        return WEEKDAY_LONG[i]
    return val
