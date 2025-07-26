from django.shortcuts import render, get_object_or_404
from .models_blog import BlogPost, BlogTag
from django.core.paginator import Paginator

def blog_index(request):
    posts = BlogPost.objects.filter(published=True).order_by('-created_at')
    q = request.GET.get('q', '').strip()
    tag = request.GET.get('tag', '').strip()
    author = request.GET.get('author', '').strip()
    if q:
        posts = posts.filter(title__icontains=q) | posts.filter(content__icontains=q) | posts.filter(tags__name__icontains=q)
        posts = posts.distinct()
    if tag:
        posts = posts.filter(tags__id=tag)
    if author:
        posts = posts.filter(author__id=author)
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    tags = BlogTag.objects.all().order_by('name')
    # Get all authors who have blog posts
    from django.contrib.auth import get_user_model
    User = get_user_model()
    authors = User.objects.filter(blogpost__published=True).distinct().order_by('first_name', 'last_name')
    return render(request, 'blog/index.html', {'page_obj': page_obj, 'tags': tags, 'authors': authors, 'selected_tag': tag, 'selected_author': author, 'q': q})

def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    tags = BlogTag.objects.all().order_by('name')
    return render(request, 'blog/detail.html', {'post': post, 'tags': tags})
