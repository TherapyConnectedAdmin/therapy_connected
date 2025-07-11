from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

# Temporary in-memory store for tokens (use a model for production)
confirmation_tokens = {}

class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(username=email, email=email, password=password, is_active=False)
            token = get_random_string(32)
            confirmation_tokens[token] = user.id
            confirm_url = request.build_absolute_uri(f'/users/confirm/{token}/')
            send_mail(
                'Confirm your email',
                f'Click the link to confirm your email: {confirm_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            messages.success(request, 'Registration successful! Please check your email to confirm your account.')
            return redirect('register')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

def confirm_email(request, token):
    user_id = confirmation_tokens.get(token)
    if user_id:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        del confirmation_tokens[token]
        messages.success(request, 'Email confirmed! You can now log in.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid or expired confirmation link.')
        return redirect('register')

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None and user.is_active:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid credentials or inactive account.')
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')

def logout_view(request):
    logout(request)
    return redirect('login')
