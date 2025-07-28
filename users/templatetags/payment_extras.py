from django import template
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    """Add N days to a date string (Y-m-d) and return a date object."""
    try:
        date_obj = datetime.strptime(value, '%Y-%m-%d')
        return date_obj + timedelta(days=int(days))
    except Exception:
        return value

@register.filter
def add_years(value, years):
    """Add N years to a date string (Y-m-d) and return a date object."""
    try:
        date_obj = datetime.strptime(value, '%Y-%m-%d')
        return date_obj.replace(year=date_obj.year + int(years))
    except Exception:
        return value
