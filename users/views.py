from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# AJAX endpoint to update subscription plan before payment
@csrf_exempt
def update_subscription(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        plan_interval = data.get('plan_interval', 'month')
        # Normalize interval to match payment view logic
        if plan_interval in ['month', 'monthly']:
            session_interval = 'monthly'
        elif plan_interval in ['year', 'annual']:
            session_interval = 'annual'
        else:
            session_interval = 'monthly'
        if plan_id:
            request.session['selected_plan_id'] = plan_id
            request.session['selected_plan_interval'] = session_interval
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm
from django import forms
from django.conf import settings
from django.utils.crypto import get_random_string
from acs_email_service import AcsEmailService
import stripe
from users.models_profile import TherapistProfile
from users.models import TherapistProfileStats
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

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
                        return redirect('profile_wizard')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid credentials or inactive account.')
    else:
        form = UserLoginForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def dashboard(request):
    from users.models_blog import BlogPost
    profile = TherapistProfile.objects.filter(user=request.user).first()
    stats = None
    if profile:
        today = timezone.now().date()
        stat_obj = TherapistProfileStats.objects.filter(therapist=request.user, date=today).first()
        stats = {
            'visit_count': stat_obj.profile_clicks if stat_obj else 0,
            'contact_count': stat_obj.contact_clicks if stat_obj else 0,
            'search_impressions': stat_obj.search_impressions if stat_obj else 0,
            'search_rank': stat_obj.search_rank if stat_obj else None,
            'last_viewed_at': profile.last_viewed_at,
        }
    # Get user's blog posts
    from django.core.paginator import Paginator
    user_blog_posts_qs = BlogPost.objects.filter(author=request.user).order_by('-created_at')
    page_number = request.GET.get('page', 1)
    paginator = Paginator(user_blog_posts_qs, 10)
    user_blog_posts = paginator.get_page(page_number)
    return render(request, 'users/dashboard.html', {
        'stats': stats,
        'user': request.user,
        'user_blog_posts': user_blog_posts,
        'paginator': paginator,
        'page_obj': user_blog_posts
    })

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
        # Always use latest selected plan/interval from session
        selected_plan_id = request.session.get('selected_plan_id')
        selected_plan_interval = request.session.get('selected_plan_interval', 'monthly')
        sub = Subscription.objects.filter(user=user).last()
        if sub and selected_plan_id:
            from users.models import SubscriptionType
            try:
                plan = SubscriptionType.objects.get(id=selected_plan_id)
                interval = selected_plan_interval
                sub.subscription_type = plan
                sub.interval = interval
                sub.stripe_customer_id = customer.id
                sub.stripe_payment_method_id = payment_method_id
                if interval == 'monthly':
                    price_id = plan.stripe_plan_id_monthly
                else:
                    price_id = plan.stripe_plan_id_annual
                stripe_sub = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': price_id}],
                    default_payment_method=payment_method_id,
                    expand=["latest_invoice.payment_intent"]
                )
                sub.stripe_subscription_id = stripe_sub.id
                sub.save()
            except SubscriptionType.DoesNotExist:
                pass
        # Set onboarding_status to 'pending_profile_completion' after payment
        user.onboarding_status = 'pending_profile_completion'
        user.save()
        # Redirect to profile wizard after payment
        return redirect('profile_wizard')
    # Get intended subscription plan from session
    from users.models import SubscriptionType
    selected_plan_id = request.session.get('selected_plan_id')
    selected_plan_interval = request.session.get('selected_plan_interval', 'monthly')
    subscription = None
    plans = SubscriptionType.objects.filter(active=True).order_by('price_monthly')
    if selected_plan_id:
        try:
            plan = SubscriptionType.objects.get(id=selected_plan_id)
            # Build subscription info for template
            if selected_plan_interval == 'monthly':
                price = plan.price_monthly
                frequency = 'month'
            else:
                price = plan.price_annual
                frequency = 'year'
            subscription = {
                'name': plan.name,
                'price': price,
                'currency': 'USD',
                'frequency': frequency
            }
        except SubscriptionType.DoesNotExist:
            pass
    return render(request, 'users/payment.html', {
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
        'subscription': subscription,
        'plans': plans
    })

def therapist_profile(request, user_id):
    from users.models_profile import TherapistProfile
    from users.models import TherapistProfileStats
    from django.utils import timezone
    profile = TherapistProfile.objects.filter(user__id=user_id).first()
    if not profile:
        return HttpResponse('Profile not found', status=404)
    # Increment profile click
    today = timezone.now().date()
    stats, _ = TherapistProfileStats.objects.get_or_create(therapist=profile.user, date=today)
    stats.profile_clicks += 1
    stats.save()
    # Optionally update last_viewed_at
    profile.last_viewed_at = timezone.now()
    profile.save()
    return render(request, 'users/therapist_profile.html', {'profile': profile})

def contact_therapist(request, user_id):
    from users.models_profile import TherapistProfile
    from users.models import TherapistProfileStats
    from django.utils import timezone
    profile = TherapistProfile.objects.filter(user__id=user_id).first()
    if not profile:
        return HttpResponse('Profile not found', status=404)
    # Increment contact click
    today = timezone.now().date()
    stats, _ = TherapistProfileStats.objects.get_or_create(therapist=profile.user, date=today)
    stats.contact_clicks += 1
    stats.save()
    # Render minimal template with mailto link
    return render(request, 'users/contact_redirect.html', {'email_address': profile.email_address})

