from django.urls import path, re_path
from django.views.generic import RedirectView
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
    # Legacy path retained (temporary) – redirect to new canonical /therapists/<slug>/
    path('t/<slug:slug>/', RedirectView.as_view(pattern_name='therapist_profile_public_slug', permanent=True), name='public_therapist_profile_legacy'),
    path('contact/<int:user_id>/', views.contact_therapist, name='contact_therapist'),
    path('update_subscription/', views.update_subscription, name='update_subscription'),
    path('api/profile_click/', views.ajax_profile_click, name='ajax_profile_click'),
    path('api/therapists/<int:user_id>/profile_full/', views.api_full_profile, name='api_full_profile'),
    # Profile edit APIs
    path('api/profile/me/', views.api_profile_me, name='api_profile_me'),
    path('api/profile/update/', views.api_profile_update, name='api_profile_update'),
    path('api/profile/submit/', views.api_profile_submit, name='api_profile_submit'),
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
    # Members area
    path('members/', views.members_home, name='members_home'),
    path('members/profile/', views.members_profile, name='members_profile'),
    path('members/account/', views.members_account, name='members_account'),
    path('members/account/email/', views.members_account_email, name='members_account_email'),
    path('members/account/password/', views.members_account_password, name='members_account_password'),
    path('members/account/billing/', views.members_account_billing, name='members_account_billing'),
    path('members/account/update_payment_method/', views.members_account_update_payment_method, name='members_account_update_payment_method'),
    path('members/account/delete/', views.members_account_delete, name='members_account_delete'),
    path('members/account/change_plan/', views.members_account_change_plan, name='members_account_change_plan'),
    path('members/account/cancel/', views.members_account_cancel_subscription, name='members_account_cancel_subscription'),
    path('members/feed/', views.members_feed, name='members_feed'),
    path('members/connections/', views.members_connections, name='members_connections'),
    path('members/connections/invitations/', views.members_invitations, name='members_invitations'),
    path('members/connections/my/', views.members_my_connections, name='members_my_connections'),
    path('members/blog/', views.members_blog, name='members_blog'),
    path('members/blog/<slug:slug>/', views.members_blog_detail, name='members_blog_detail'),
    path('members/stats/', views.members_stats, name='members_stats'),
    # Feed APIs
    path('api/feed/<int:post_id>/react/', views.api_feed_react, name='api_feed_react'),
    path('api/feed/<int:post_id>/comment/', views.api_feed_comment, name='api_feed_comment'),
    path('api/feed/<int:post_id>/media/', views.api_feed_media_upload, name='api_feed_media_upload'),
    path('api/feed/<int:post_id>/repost/', views.api_feed_repost, name='api_feed_repost'),
    path('api/feed/<int:post_id>/', views.api_feed_post_item, name='api_feed_post_item'),
    path('api/feed/<int:post_id>/reactions/', views.api_feed_reactions, name='api_feed_reactions'),
    path('api/feed/new_count/', views.api_feed_new_count, name='api_feed_new_count'),
    # Stock images search for composer
    path('api/feed/stock_images/', views.api_feed_stock_images, name='api_feed_stock_images'),
    path('api/proxy/image/', views.api_proxy_image, name='api_proxy_image'),
    # Connections APIs
    path('api/connections/<int:conn_id>/accept/', views.api_connection_accept, name='api_connection_accept'),
    path('api/connections/<int:conn_id>/delete/', views.api_connection_delete, name='api_connection_delete'),
    path('api/connections/request/<int:user_id>/', views.api_connection_request, name='api_connection_request'),
    path('api/connections/discover/', views.api_connections_discover, name='api_connections_discover'),
]