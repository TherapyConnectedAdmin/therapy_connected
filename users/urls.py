from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('confirm/<str:token>/', views.confirm_email, name='confirm_email'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('payment/', views.payment, name='payment'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
]