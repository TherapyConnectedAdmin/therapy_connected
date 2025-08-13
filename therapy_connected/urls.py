"""
URL configuration for therapy_connected project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from users.sitemaps import TherapistProfileSitemap
from . import views
from users import views as user_views  # for public_therapist_profile if needed

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('users/', include('users.urls')),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscribe/pay/', views.select_plan, name='select_plan'),
    path('set_zip/', views.set_zip, name='set_zip'),
    path('geo_zip/', views.geo_zip, name='geo_zip'),
    path('therapists/', views.therapists_page, name='therapists_page'),
    # SEO-friendly therapist public profile pages (slug under /therapists/)
    path('therapists/<slug:slug>/', user_views.public_therapist_profile, name='therapist_profile_public_slug'),
    # XML sitemap exposing therapist profile slugs
    path('sitemap.xml', sitemap, {'sitemaps': {'therapists': TherapistProfileSitemap}}, name='django.contrib.sitemaps.views.sitemap'),
    path('features/', views.features_page, name='features_page'),
    path('pricing/', views.pricing_page, name='pricing_page'),
    path('about/', views.about_page, name='about_page'),
    path('', include('users.urls_blog')),
]

# Serve media files in development (when not using S3)
if settings.DEBUG and getattr(settings, 'MEDIA_URL', None) and getattr(settings, 'MEDIA_ROOT', None):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

