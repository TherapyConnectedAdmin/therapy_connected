from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm
from django import forms
from django.conf import settings
from django.utils.crypto import get_random_string
from acs_email_service import AcsEmailService
import stripe

# Temporary in-memory store for tokens (use a model for production)
confirmation_tokens = {}

# Initialize ACS Email Service
service = AcsEmailService(
    connection_string=settings.ACS_CONNECTION_STRING,
    sender_address=settings.ACS_SENDER_ADDRESS
)

class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

def register(request):
    selected_plan_id = request.session.get('selected_plan_id')
    selected_plan_interval = request.session.get('selected_plan_interval', 'monthly')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = User.objects.create_user(username=email, email=email, password=password, is_active=False)
            # Save subscription type and interval if selected
            if selected_plan_id:
                from .models import SubscriptionType, Subscription
                try:
                    plan = SubscriptionType.objects.get(id=selected_plan_id)
                    Subscription.objects.create(user=user, subscription_type=plan, interval=selected_plan_interval, active=True)
                except SubscriptionType.DoesNotExist:
                    pass
            token = get_random_string(32)
            confirmation_tokens[token] = user.id
            confirm_url = request.build_absolute_uri(f'/users/confirm/{token}/')
            subject = 'Confirm your email'
            plain_text = f'Click the link to confirm your email: {confirm_url}'
            success, message_id = service.send_email(
                recipient=email,
                subject=subject,
                plain_text=plain_text,
                display_name=email
            )
            # Set onboarding_status to 'pending_email_confirmation' after email sent
            user.onboarding_status = 'pending_email_confirmation'
            user.save()
            if success:
                messages.success(request, 'Registration successful! Please check your email to confirm your account.')
            else:
                messages.error(request, f'Failed to send confirmation email: {message_id}')
            return redirect('register')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

def confirm_email(request, token):
    user_id = confirmation_tokens.get(token)
    if user_id:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.onboarding_status = 'pending_payment'
        user.save()
        del confirmation_tokens[token]
        messages.success(request, 'Email confirmed! Please enter your payment details to complete registration.')
        return redirect('payment')
    else:
        messages.error(request, 'Invalid or expired confirmation link.')
        return redirect('register')

def login_view(request):
    next_url = request.GET.get('next')
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None and user.is_active:
                login(request, user)
                # If next is set, always redirect with a fresh GET
                if next_url:
                    return redirect(next_url)
                # Redirect based on onboarding_status
                if hasattr(user, 'onboarding_status'):
                    if user.onboarding_status == 'payment':
                        return redirect('payment')
                    elif user.onboarding_status == 'pending_profile_completion':
                        return redirect('complete_profile')
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

from django.views.decorators.cache import never_cache

@login_required
@never_cache
def payment(request):
    import stripe
    from django.conf import settings
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if request.method == 'POST':
        payment_method_id = request.POST.get('payment_method_id')
        cardholder = request.POST.get('cardholder')
        user = request.user
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=cardholder
        )
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer.id
        )
        # Save Stripe IDs to user's subscription and create Stripe subscription
        from users.models import Subscription, SubscriptionType
        sub = Subscription.objects.filter(user=user).last()
        if sub:
            sub.stripe_customer_id = customer.id
            sub.stripe_payment_method_id = payment_method_id
            # Get Stripe price ID from SubscriptionType
            plan = sub.subscription_type
            interval = sub.interval
            if interval == 'monthly':
                price_id = plan.stripe_plan_id_monthly
            else:
                price_id = plan.stripe_plan_id_annual
            # Create Stripe subscription
            stripe_sub = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                default_payment_method=payment_method_id,
                expand=["latest_invoice.payment_intent"]
            )
            sub.stripe_subscription_id = stripe_sub.id
            sub.save()
        # Set onboarding_status to 'pending_profile_completion' after payment
        user.onboarding_status = 'pending_profile_completion'
        user.save()
        # Redirect to dashboard after payment (simulate success)
        return redirect('dashboard')
    return render(request, 'users/payment.html', {'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY})

from .forms_profile import TherapistProfileForm
from .models_profile import TherapistProfile

@login_required
def complete_profile(request):
    user = request.user
    if hasattr(user, 'onboarding_status') and user.onboarding_status != 'pending_profile_completion':
        return redirect('dashboard')
    try:
        profile = TherapistProfile.objects.get(user=user)
    except TherapistProfile.DoesNotExist:
        profile = None
    if request.method == 'POST':
        form = TherapistProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.save()
            user.onboarding_status = 'active'
            user.save(update_fields=['onboarding_status'])
            messages.success(request, 'Profile completed!')
            return redirect('dashboard')
    else:
        initial = {}
        if not profile:
            initial['user'] = user.pk
        form = TherapistProfileForm(instance=profile, initial=initial)
    return render(request, 'users/complete_profile.html', {'form': form})
