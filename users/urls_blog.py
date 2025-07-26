from django.urls import path
from .views_blog import blog_index, blog_detail

urlpatterns = [
    path('blog/', blog_index, name='blog_index'),
    path('blog/<slug:slug>/', blog_detail, name='blog_detail'),
]
