from django.urls import path
from .views_blog import blog_index, blog_detail, user_blog_list, user_blog_create

urlpatterns = [
    path('blog/', blog_index, name='blog_index'),
    path('blog/<slug:slug>/', blog_detail, name='blog_detail'),
    path('my-blogs/', user_blog_list, name='user_blog_list'),
    path('my-blogs/new/', user_blog_create, name='user_blog_create'),
]
