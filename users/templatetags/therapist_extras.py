
from django import template
from users.location_utils import get_primary_location as shared_get_primary_location
import os

register = template.Library()


@register.filter
def get_primary_location(locations):
    """Return the primary location from a queryset of locations, or None if not found. Uses shared utility."""
    return shared_get_primary_location(locations)


@register.simple_tag
def profile_photo_variant(tp, variant_label="medium", fmt="jpg"):
    """Return URL for a given therapist profile photo variant if metadata exists; fallback to original.
    Usage: {% profile_photo_variant therapist 'thumb' %}
    """
    if not getattr(tp, 'profile_photo', None):
        return ''
    meta = getattr(tp, 'profile_photo_meta', None) or {}
    variants = meta.get('variants') or {}
    v = variants.get(variant_label)
    if v:
        name = v.get(fmt)
        if name:
            base_dir = os.path.dirname(tp.profile_photo.url)
            return f"{base_dir}/{name}"
    # fallback
    return tp.profile_photo.url

@register.simple_tag
def profile_photo_srcset(tp, fmt_preference="webp"):
    """Build a srcset string using available variants; prefer webp else jpg."""
    if not getattr(tp, 'profile_photo', None):
        return ''
    meta = getattr(tp, 'profile_photo_meta', None) or {}
    variants = meta.get('variants') or {}
    if not variants:
        return ''
    base_dir = os.path.dirname(tp.profile_photo.url)
    parts = []
    order = [('thumb', 160), ('medium', 600), ('large', 1200)]
    for label, width in order:
        v = variants.get(label)
        if not v:
            continue
        name = v.get(fmt_preference) or v.get('jpg')
        if not name:
            continue
        parts.append(f"{base_dir}/{name} {width}w")
    return ', '.join(parts)


# Generic image variant helpers (GalleryImage, BlogPost) expecting image + image_meta fields
def _generic_variant(obj, variant_label, fmt):
    if not getattr(obj, 'image', None):
        return ''
    meta = getattr(obj, 'image_meta', None) or {}
    variants = meta.get('variants') or {}
    v = variants.get(variant_label)
    if v:
        name = v.get(fmt) or v.get('jpg')
        if name:
            base_dir = os.path.dirname(obj.image.url)
            return f"{base_dir}/{name}"
    return getattr(obj.image, 'url', '')

@register.simple_tag
def image_variant(obj, variant_label='medium', fmt='jpg'):
    return _generic_variant(obj, variant_label, fmt)

@register.simple_tag
def image_srcset(obj, fmt_preference='webp'):
    if not getattr(obj, 'image', None):
        return ''
    meta = getattr(obj, 'image_meta', None) or {}
    variants = meta.get('variants') or {}
    if not variants:
        return ''
    base_dir = os.path.dirname(obj.image.url)
    order = [('thumb', 160), ('medium', 600), ('large', 1200)]
    parts = []
    for label, width in order:
        v = variants.get(label)
        if not v:
            continue
        name = v.get(fmt_preference) or v.get('jpg')
        if name:
            parts.append(f"{base_dir}/{name} {width}w")
    return ', '.join(parts)

@register.filter
def to_ampm(value):
    """Convert 'HH:MM' 24h string to 'H:MM AM/PM'. Leaves value untouched if parsing fails."""
    if not value or not isinstance(value, str) or ':' not in value:
        return value
    try:
        h_s, m_s = value.split(':', 1)
        h = int(h_s)
        m = int(m_s[:2])
        ampm = 'PM' if h >= 12 else 'AM'
        hr12 = ((h + 11) % 12) + 1
        return f"{hr12}:{m:02d} {ampm}"
    except Exception:
        return value

