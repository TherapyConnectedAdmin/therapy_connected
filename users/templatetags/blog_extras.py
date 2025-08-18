from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

TOKEN_RE = re.compile(r"\[\[\s*media\s*:\s*(\d+)\s*\]\]")

@register.filter
def has_media_tokens(content: str) -> bool:
    try:
        return bool(TOKEN_RE.search(content or ''))
    except Exception:
        return False

@register.simple_tag
def render_blog_content(post):
    """
    Replace tokens like [[media:1]] with the corresponding attached BlogMedia HTML.
    1-based index according to ordered post.media.all(). Max 8.
    """
    try:
        content = post.content or ''
        media_list = list(getattr(post, 'media').all()[:8]) if hasattr(post, 'media') else []
        if not media_list:
            return mark_safe(content)
        def repl(m):
            try:
                idx = int(m.group(1)) - 1
            except Exception:
                idx = -1
            if 0 <= idx < len(media_list):
                item = media_list[idx]
                if getattr(item, 'type', '') == 'video':
                    return f'<video class="w-full rounded" controls src="{item.file.url}"></video>'
                else:
                    return f'<img class="w-full rounded" src="{item.file.url}" alt="" />'
            return ''
        html = TOKEN_RE.sub(repl, content)
        return mark_safe(html)
    except Exception:
        return mark_safe(getattr(post, 'content', '') or '')
