from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models_blog import BlogPost, BlogTag, BlogMedia
from django.db.models import Q
from django.db import models as dj_models
from django.core.paginator import Paginator
from .forms_blog import BlogPostForm
from django.utils.text import slugify
from django.http import JsonResponse
from django.urls import reverse
from django.utils.http import urlencode



@login_required
def user_blog_edit(request, pk):
    post = get_object_or_404(BlogPost, pk=pk, author=request.user)
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            if not post.slug:
                base_slug = slugify(post.title)
                slug = base_slug
                i = 1
                while BlogPost.objects.filter(slug=slug).exclude(pk=post.pk).exists():
                    slug = f"{base_slug}-{i}"
                    i += 1
                post.slug = slug
            post.save()
            form.save_m2m()
            # Handle multiple media (cap 8)
            files = request.FILES.getlist('media') or []
            # Parse optional media_meta JSON mapping
            import json as _json
            try:
                media_meta_map = _json.loads(request.POST.get('media_meta') or '{}')
            except Exception:
                media_meta_map = {}
            max_items = 8
            pos = post.media.aggregate(dj_models.Max('position')).get('position__max') or 0
            for idx, f in enumerate(files[:max_items]):
                ctype = (getattr(f, 'content_type', '') or '').lower()
                name = getattr(f, 'name', '') or ''
                ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                def guess_type():
                    if ctype.startswith('image/') or ext in {'jpg','jpeg','png','gif','webp','bmp'}:
                        return 'image'
                    if ctype.startswith('video/') or ext in {'mp4','mov','m4v','webm','avi','mkv'}:
                        return 'video'
                    return ''
                mtype = guess_type()
                if not mtype:
                    continue
                meta = None
                if isinstance(media_meta_map, dict):
                    meta = media_meta_map.get(getattr(f, 'name', ''), None)
                BlogMedia.objects.create(post=post, file=f, type=mtype, meta=(meta or {}), position=pos+idx+1)
            return redirect('members_blog')
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'users/user_blog_form.html', {'form': form, 'edit_mode': True, 'post': post})


def blog_index(request):
    posts = BlogPost.objects.filter(published=True).filter(
        Q(visibility__in=['public','both'])
    ).select_related('author').prefetch_related('tags')
    q = request.GET.get('q', '').strip()
    tag = request.GET.get('tag', '').strip()
    author = request.GET.get('author', '').strip()
    sort = request.GET.get('sort', '').strip() or 'recent'

    if q:
        posts = posts.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(tags__name__icontains=q)
        ).distinct()
    if tag:
        posts = posts.filter(tags__id=tag)
    if author:
        posts = posts.filter(author__id=author)

    # Sorting
    if sort == 'recent':
        posts = posts.order_by('-created_at')
    elif sort == 'oldest':
        posts = posts.order_by('created_at')
    elif sort == 'title':
        posts = posts.order_by('title')
    elif sort == 'title_desc':
        posts = posts.order_by('-title')
    elif sort == 'author':
        posts = posts.order_by('author__first_name', 'author__last_name', '-created_at')
    else:
        posts = posts.order_by('-created_at')

    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    tags = BlogTag.objects.all().order_by('name')
    # Get all authors who have blog posts
    from django.contrib.auth import get_user_model
    User = get_user_model()
    authors = User.objects.filter(blogpost__published=True).distinct().order_by('first_name', 'last_name')
    # Fallback: if no authors resolved but posts exist (edge case), derive from posts
    if not authors.exists() and posts.exists():
        author_ids = posts.values_list('author_id', flat=True)
        authors = User.objects.filter(id__in=author_ids).order_by('first_name', 'last_name')
    return render(request, 'blog/index.html', {
        'page_obj': page_obj,
        'tags': tags,
        'authors': authors,
        'selected_tag': tag,
        'selected_author': author,
        'selected_sort': sort,
        'q': q,
    })


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True, visibility__in=['public','both'])
    tags = BlogTag.objects.all().order_by('name')
    # Sidebar data
    recent_posts = BlogPost.objects.filter(published=True, visibility__in=['public','both']).exclude(id=post.id).order_by('-created_at')[:6]
    related_posts = BlogPost.objects.filter(published=True, visibility__in=['public','both'], tags__in=post.tags.all()).exclude(id=post.id).distinct().order_by('-created_at')[:6]
    # Simple popular tags: top 10 by usage count
    popular_tags = BlogTag.objects.all().order_by('name')[:10]
    return render(request, 'blog/detail.html', {
        'post': post,
        'tags': tags,
        'recent_posts': recent_posts,
        'related_posts': related_posts,
        'popular_tags': popular_tags,
    })


@login_required
def user_blog_list(request):
    posts = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'users/user_blog_list.html', {'posts': posts})

@login_required
def user_blog_create(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
        is_ajax = request.headers.get('x-requested-with', '').lower() == 'xmlhttprequest'
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if not post.slug:
                base_slug = slugify(post.title)
                slug = base_slug
                i = 1
                while BlogPost.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{i}"
                    i += 1
                post.slug = slug
            post.save()
            form.save_m2m()
            # Handle multiple media (cap 8)
            files = request.FILES.getlist('media') or []
            import json as _json, logging
            logger = logging.getLogger(__name__)
            try:
                media_meta_map = _json.loads(request.POST.get('media_meta') or '{}')
            except Exception:
                media_meta_map = {}
            # Map original upload filename -> BlogMedia object for later content replacement
            filename_to_media = {}
            try:
                for idx, f in enumerate(files[:8]):
                    ctype = (getattr(f, 'content_type', '') or '').lower()
                    name = getattr(f, 'name', '') or ''
                    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                    def guess_type():
                        if ctype.startswith('image/') or ext in {'jpg','jpeg','png','gif','webp','bmp'}:
                            return 'image'
                        return ''
                    mtype = guess_type()
                    if not mtype:
                        continue
                    meta = None
                    if isinstance(media_meta_map, dict):
                        meta = media_meta_map.get(getattr(f, 'name', ''), None)
                    bm = BlogMedia.objects.create(post=post, file=f, type=mtype, meta=(meta or {}), position=idx+1)
                    if name:
                        filename_to_media[name] = bm
            except Exception as ex:
                logger.exception('Blog media save failed')
                if is_ajax:
                    return JsonResponse({'error': 'media_save_failed', 'detail': str(ex)}, status=500)
            # Replace editor placeholders [[MEDIA:filename]] or src=[[MEDIA:filename]] with actual URLs
            try:
                import re
                content_html = post.content or ''
                # First replace src attributes (handle single or double quotes) to preserve the rest of the <img> tag
                def _repl_attr(m):
                    fname = m.group(2)
                    bm = filename_to_media.get(fname)
                    if bm and getattr(bm.file, 'url', None) and bm.type == 'image':
                        quote = m.group(1)
                        return f'src={quote}{bm.file.url}{quote}'
                    return m.group(0)
                content_html = re.sub(r'src=([\'\"])\[\[MEDIA:([^\]]+)\]\]\1', _repl_attr, content_html)
                # Replace any standalone tokens with <img> tags
                def _repl_token(m):
                    fname = m.group(1)
                    bm = filename_to_media.get(fname)
                    if bm and getattr(bm.file, 'url', None) and bm.type == 'image':
                        return f'<img src="{bm.file.url}" alt="" />'
                    return ''
                content_html = re.sub(r'\[\[MEDIA:([^\]]+)\]\]', _repl_token, content_html)
                if content_html != (post.content or ''):
                    post.content = content_html
                    post.save(update_fields=['content','updated_at'])
            except Exception:
                # On any error, keep original content
                pass
            if is_ajax:
                from django.urls import reverse
                return JsonResponse({'ok': True, 'redirect': reverse('members_blog')})
            return redirect('members_blog')
        else:
            if is_ajax:
                return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = BlogPostForm()
    return render(request, 'users/user_blog_form.html', {'form': form})

@login_required
def user_blog_update_visibility(request, pk):
    """Update visibility (and optionally published) for a blog post owned by the user.
    Accepts POST with fields: visibility (required), published (optional: 'on'/truthy).
    Redirects back to members_blog preserving q/sort/page when provided.
    """
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method != 'POST':
        return redirect('members_blog')
    # Server-side guard: only author can update
    if post.author_id != request.user.id:
        return redirect('members_blog')
    vis = (request.POST.get('visibility') or '').strip()
    valid = {k for k, _ in BlogPost.VISIBILITY_CHOICES}
    if vis not in valid:
        # Ignore invalid values silently for UX; keep old visibility
        pass
    else:
        post.visibility = vis
    if 'published' in request.POST:
        # Treat presence as boolean toggle; accept common truthy values
        val = (request.POST.get('published') or '').lower()
        post.published = val in {'1','true','yes','on'}
    post.save(update_fields=['visibility','published','updated_at'])
    # Preserve filters if sent
    q = request.POST.get('q', '')
    sort = request.POST.get('sort', '')
    page = request.POST.get('page', '')
    from django.urls import reverse
    import urllib.parse as _url
    base = reverse('members_blog')
    params = { 'q': q, 'sort': sort, 'page': page }
    params = {k:v for k,v in params.items() if v}
    if params:
        return redirect(f"{base}?{_url.urlencode(params)}")
    return redirect('members_blog')


@login_required
def user_blog_delete(request, pk):
    """Delete a blog post owned by the current user.
    Accepts POST only. Redirects back to members_blog preserving q/sort/page when provided.
    Also attempts to delete associated media files from storage.
    """
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method != 'POST':
        return redirect('members_blog')
    if post.author_id != request.user.id:
        return redirect('members_blog')
    # Best-effort remove files from storage first
    try:
        for m in list(post.media.all()):
            try:
                if getattr(m, 'file', None):
                    m.file.delete(save=False)
            except Exception:
                pass
        try:
            if getattr(post, 'image', None):
                post.image.delete(save=False)
        except Exception:
            pass
    except Exception:
        pass
    # Delete the post (cascades to BlogMedia in DB)
    post.delete()
    # Preserve filters if sent
    q = request.POST.get('q', '')
    sort = request.POST.get('sort', '')
    page = request.POST.get('page', '')
    base = reverse('members_blog')
    params = {k: v for k, v in {'q': q, 'sort': sort, 'page': page}.items() if v}
    if params:
        return redirect(f"{base}?{urlencode(params)}")
    return redirect('members_blog')
