from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models_blog import BlogPost, BlogTag
from django.core.paginator import Paginator
from .forms_blog import BlogPostForm
from django.utils.text import slugify

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
            return redirect('dashboard')
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'users/user_blog_form.html', {'form': form, 'edit_mode': True, 'post': post})

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

@login_required
def user_blog_list(request):
    posts = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'users/user_blog_list.html', {'posts': posts})

@login_required
def user_blog_create(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)
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
            return redirect('dashboard')
    else:
        form = BlogPostForm()
    return render(request, 'users/user_blog_form.html', {'form': form})
