from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('payment/', views.payment, name='payment'),
    # New unified edit experience replaces wizard
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<int:user_id>/', views.therapist_profile, name='therapist_profile'),
    path('t/<slug:slug>/', views.public_therapist_profile, name='public_therapist_profile'),
    path('contact/<int:user_id>/', views.contact_therapist, name='contact_therapist'),
    path('update_subscription/', views.update_subscription, name='update_subscription'),
    path('api/profile_click/', views.ajax_profile_click, name='ajax_profile_click'),
    path('api/therapists/<int:user_id>/profile_full/', views.api_full_profile, name='api_full_profile'),
    # Profile edit APIs
    path('api/profile/me/', views.api_profile_me, name='api_profile_me'),
    path('api/profile/update/', views.api_profile_update, name='api_profile_update'),
    path('api/profile/upload/photo/', views.api_profile_upload_photo, name='api_profile_upload_photo'),
    path('api/profile/gallery/upload/', views.api_profile_gallery_upload, name='api_profile_gallery_upload'),
    path('api/profile/gallery/<int:image_id>/', views.api_profile_gallery_item, name='api_profile_gallery_item'),
    path('api/profile/video/', views.api_profile_video, name='api_profile_video'),
    path('api/profile/locations/create/', views.api_location_create, name='api_location_create'),
    path('api/profile/locations/<int:location_id>/', views.api_location_item, name='api_location_item'),
    path('api/profile/locations/<int:location_id>/office_hours/', views.api_location_office_hours, name='api_location_office_hours'),
    # Education & Credentials
    path('api/profile/educations/create/', views.api_education_create, name='api_education_create'),
    path('api/profile/educations/<int:education_id>/', views.api_education_item, name='api_education_item'),
    path('api/profile/credentials/create/', views.api_additional_credential_create, name='api_additional_credential_create'),
    path('api/profile/credentials/<int:credential_id>/', views.api_additional_credential_item, name='api_additional_credential_item'),
    # Lookup endpoints
    path('api/lookups/insurance_providers/', views.api_insurance_providers, name='api_insurance_providers'),
    path('api/lookups/therapy_types/', views.api_therapy_types, name='api_therapy_types'),
    path('api/lookups/specialties/', views.api_specialties_lookup, name='api_specialties_lookup'),
    path('api/lookups/participant_types/', views.api_participant_types, name='api_participant_types'),
    path('api/lookups/age_groups/', views.api_age_groups, name='api_age_groups'),
]