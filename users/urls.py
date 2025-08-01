from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('payment/', views.payment, name='payment'),
    path('profile-wizard/',
         __import__('users.views_profile_wizard').views_profile_wizard.TherapistProfileWizard.as_view(),
         name='profile_wizard'),
    path('profile/<int:user_id>/', views.therapist_profile, name='therapist_profile'),
    path('contact/<int:user_id>/', views.contact_therapist, name='contact_therapist'),
    path('update_subscription/', views.update_subscription, name='update_subscription'),
    path('api/profile_click/', views.ajax_profile_click, name='ajax_profile_click'),
]