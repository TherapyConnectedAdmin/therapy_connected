from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
# AJAX endpoint to increment profile clicks
@csrf_exempt
def ajax_profile_click(request):
    if request.method == "POST":
        import json
        from users.models_profile import TherapistProfile
        from users.models import TherapistProfileStats
        from django.utils import timezone
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_id = data.get("user_id")
            profile = TherapistProfile.objects.filter(user__id=user_id).first()
            if not profile:
                return JsonResponse({"success": False, "error": "Profile not found"}, status=404)
            today = timezone.now().date()
            stats, _ = TherapistProfileStats.objects.get_or_create(therapist=profile.user, date=today)
            stats.profile_clicks += 1
            stats.save()
            profile.last_viewed_at = timezone.now()
            profile.save()
            return JsonResponse({"success": True, "profile_clicks": stats.profile_clicks})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
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

def public_therapist_profile(request, slug):
    """Standalone SEO-friendly therapist profile page matching modal content.
    Adds gallery images and video gallery media for parity with in-app modal.
    """
    from django.shortcuts import get_object_or_404
    from users.models_profile import TherapistProfile
    profile = get_object_or_404(
        TherapistProfile.objects.select_related('license_type', 'gender', 'title', 'user')
        .prefetch_related(
            'locations__office_hours', 'gallery_images', 'video_gallery',
            'accepted_payment_methods__payment_method', 'types_of_therapy__therapy_type',
            'specialties__specialty', 'race_ethnicities__race_ethnicity', 'faiths__faith',
            'lgbtqia_identities__lgbtqia', 'other_identities__other_identity',
            'additional_credentials', 'educations'
        ), slug=slug)
    # Build JSON structure analogous to api_full_profile
    primary_location = profile.locations.filter(is_primary_address=True).first() or profile.locations.first()
    def office_hours(loc):
        return [
            {
                'weekday': oh.weekday,
                'is_closed': oh.is_closed,
                'by_appointment_only': oh.by_appointment_only,
                'start_time_1': oh.start_time_1,
                'end_time_1': oh.end_time_1,
                'start_time_2': oh.start_time_2,
                'end_time_2': oh.end_time_2,
                'notes': oh.notes,
            } for oh in loc.office_hours.all()
        ]
    from django.utils import timezone
    current_year = timezone.now().year
    # derive years in practice similar to api_full_profile
    candidate_years = []
    for e in profile.educations.all():
        if getattr(e, 'year_began_practice', None) and e.year_began_practice.isdigit() and len(e.year_began_practice) == 4:
            candidate_years.append(int(e.year_began_practice))
        elif getattr(e, 'year_graduated', None) and e.year_graduated.isdigit() and len(e.year_graduated) == 4:
            candidate_years.append(int(e.year_graduated))
    years_in_practice = None
    if candidate_years:
        start_year = min(candidate_years)
        if 1900 < start_year <= current_year:
            years_in_practice = current_year - start_year

    data = {
        'id': profile.user.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
        'name': f"{profile.first_name} {profile.last_name}".strip(),
        'title': profile.title.name if profile.title else None,
        'display_title': profile.display_title,
        'intro_statement': profile.intro_statement,
        'personal_statement_q1': profile.personal_statement_q1,
        'personal_statement_q2': profile.personal_statement_q2,
        'personal_statement_q3': profile.personal_statement_q3,
        'practice_name': profile.practice_name,
        'therapy_delivery_method': profile.therapy_delivery_method,
        'practice_email': profile.practice_email,
        'phone_number': profile.phone_number,
        'phone_extension': profile.phone_extension,
        'mobile_number': profile.mobile_number,
        'office_email': profile.office_email,
        'accepting_new_clients': profile.accepting_new_clients,
        'offers_intro_call': profile.offers_intro_call,
        'individual_session_cost': profile.individual_session_cost,
        'couples_session_cost': profile.couples_session_cost,
        'sliding_scale_pricing_available': profile.sliding_scale_pricing_available,
        'finance_note': profile.finance_note,
        'credentials_note': profile.credentials_note,
        'profile_photo_url': profile.profile_photo.url if profile.profile_photo else None,
        'practice_website_url': profile.practice_website_url,
        'facebook_url': profile.facebook_url,
        'instagram_url': profile.instagram_url,
        'linkedin_url': profile.linkedin_url,
        'twitter_url': profile.twitter_url,
        'tiktok_url': profile.tiktok_url,
        'youtube_url': profile.youtube_url,
        'therapy_types_note': profile.therapy_types_note,
        'specialties_note': profile.specialties_note,
        'license_type': profile.license_type.name if profile.license_type else None,
        'license_type_description': profile.license_type.description if profile.license_type else None,
        'license_type_short': profile.license_type.short_description if profile.license_type else None,
        'license_number': profile.license_number,
        'license_expiration': profile.license_expiration,
        'license_state': profile.license_state,
        'gender': profile.gender.name if profile.gender else None,
    'years_in_practice': years_in_practice,
        'city': primary_location.city if primary_location else None,
        'state': primary_location.state if primary_location else None,
        'locations': [
            {
                'practice_name': loc.practice_name,
                'street_address': loc.street_address,
                'address_line_2': loc.address_line_2,
                'city': loc.city,
                'state': loc.state,
                'zip': loc.zip,
                'is_primary_address': loc.is_primary_address,
                'lat': None,
                'lng': None,
                'office_hours': office_hours(loc),
            } for loc in profile.locations.all()
        ],
        # Populated below
        'gallery_images': [],
        'video_gallery': [],
        'accepted_payment_methods': [sel.payment_method.name for sel in profile.accepted_payment_methods.all()],
        'types_of_therapy': [sel.therapy_type.name for sel in profile.types_of_therapy.all()],
        'therapy_types': [sel.therapy_type.name for sel in profile.types_of_therapy.all()],  # alias for modal
        'other_therapy_types': [ot.therapy_type for ot in profile.other_therapy_types.all()],
        'specialties': [
            {
                'name': sp.specialty.name if sp.specialty else '',
                'is_top': sp.is_top_specialty,
            } for sp in profile.specialties.all()
        ],
        'top_specialties': [sp.specialty.name for sp in profile.specialties.filter(is_top_specialty=True) if sp.specialty],
        'race_ethnicities': [s.race_ethnicity.name for s in profile.race_ethnicities.all() if s.race_ethnicity],
        'faiths': [s.faith.name for s in profile.faiths.all() if s.faith],
        'lgbtqia_identities': [s.lgbtqia.name for s in profile.lgbtqia_identities.all() if s.lgbtqia],
        'other_identities': [s.other_identity.name for s in profile.other_identities.all() if s.other_identity],
        'insurance_details': [
            {
                'provider': ins.provider.name if ins.provider else '',
                'out_of_network': ins.out_of_network,
            } for ins in profile.insurance_details.all()
        ],
        'additional_credentials': [
            {
                'type': ac.additional_credential_type,
                'organization_name': ac.organization_name,
                'id_number': ac.id_number,
                'year_issued': ac.year_issued,
            } for ac in profile.additional_credentials.all()
        ],
        'educations': [
            {
                'school': ed.school,
                'degree_diploma': ed.degree_diploma,
                'year_graduated': ed.year_graduated,
            } for ed in profile.educations.all()
        ],
        'participant_types': [pt.name for pt in profile.participant_types.all()],
        'age_groups': [ag.name for ag in profile.age_groups.all()],
        'areas_of_expertise': [ae.expertise for ae in profile.areas_of_expertise.all()],
    }
    # Gallery Images (match modal expectations: url, caption, is_primary)
    images = []
    for gi in profile.gallery_images.all():
        try:
            url = gi.image.url
        except Exception:
            url = None
        if not url:
            continue
        images.append({
            'url': url,
            'caption': gi.caption,
            'is_primary': gi.is_primary,
        })
    data['gallery_images'] = images

    # Video Gallery (provide video_url + caption)
    vids = []
    for vg in profile.video_gallery.all():
        try:
            vurl = vg.video.url
        except Exception:
            vurl = None
        if not vurl:
            continue
        vids.append({
            'video_url': vurl,
            'caption': vg.caption,
        })
    data['video_gallery'] = vids
    # Render with full modal partial in standalone mode
    import json
    return render(request, 'users/therapist_profile_public_full.html', {
        'profile_obj': profile,
        'serialized': json.dumps(data),
    })

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

# JSON API: full therapist profile by user id
def api_full_profile(request, user_id):
    from django.shortcuts import get_object_or_404
    from users.models_profile import (
        TherapistProfile,
        Specialty,
        TherapyTypeSelection,
        OtherTherapyType,
        AreasOfExpertise,
        PaymentMethodSelection,
        InsuranceDetail,
        GalleryImage,
        VideoGallery,
        Education,
        AdditionalCredential,
        Location,
        OfficeHour,
    )
    from django.utils import timezone
    profile = get_object_or_404(
        TherapistProfile.objects.select_related('license_type', 'gender', 'title', 'user')
        .prefetch_related('locations__office_hours'),
        user__id=user_id
    )
    # Primary location
    primary_location = profile.locations.filter(is_primary_address=True).first() or profile.locations.first()
    def img_url(image_field):
        try:
            return image_field.url if image_field else None
        except Exception:
            return None
    # Years in practice (derive from earliest education.year_began_practice or year_graduated)
    current_year = timezone.now().year
    candidate_years = []
    for e in profile.educations.all():
        if e.year_began_practice and e.year_began_practice.isdigit() and len(e.year_began_practice) == 4:
            candidate_years.append(int(e.year_began_practice))
        elif e.year_graduated and e.year_graduated.isdigit() and len(e.year_graduated) == 4:
            candidate_years.append(int(e.year_graduated))
    years_in_practice = None
    if candidate_years:
        start_year = min(candidate_years)
        if 1900 < start_year <= current_year:
            years_in_practice = current_year - start_year

    data = {
        'id': profile.user.id,
        'first_name': profile.first_name,
        'last_name': profile.last_name,
        'name': f"{profile.first_name} {profile.last_name}".strip(),
        'title': profile.title.name if profile.title else None,
        'display_title': profile.display_title,
        'intro_statement': profile.intro_statement,
        'personal_statement_q1': profile.personal_statement_q1,
        'personal_statement_q2': profile.personal_statement_q2,
        'personal_statement_q3': profile.personal_statement_q3,
        'practice_name': profile.practice_name,
    'therapy_delivery_method': profile.therapy_delivery_method,
        'practice_email': profile.practice_email,
        'phone_number': profile.phone_number,
        'phone_extension': profile.phone_extension,
        'mobile_number': profile.mobile_number,
        'office_email': profile.office_email,
        'accepting_new_clients': profile.accepting_new_clients,
        'offers_intro_call': profile.offers_intro_call,
        'individual_session_cost': profile.individual_session_cost,
        'couples_session_cost': profile.couples_session_cost,
        'sliding_scale_pricing_available': profile.sliding_scale_pricing_available,
        'finance_note': profile.finance_note,
        'credentials_note': profile.credentials_note,
        'profile_photo_url': img_url(profile.profile_photo),
        'practice_website_url': profile.practice_website_url,
        'facebook_url': profile.facebook_url,
        'instagram_url': profile.instagram_url,
        'linkedin_url': profile.linkedin_url,
        'twitter_url': profile.twitter_url,
        'tiktok_url': profile.tiktok_url,
        'youtube_url': profile.youtube_url,
        'therapy_types_note': profile.therapy_types_note,
        'specialties_note': profile.specialties_note,
        'license_type': profile.license_type.name if profile.license_type else None,
        'license_type_description': profile.license_type.description if profile.license_type else None,
    'license_type_short': profile.license_type.short_description if profile.license_type else None,
        'license_number': profile.license_number,
        'license_expiration': profile.license_expiration,
        'license_state': profile.license_state,
        'gender': profile.gender.name if profile.gender else None,
        'years_in_practice': years_in_practice,
        'city': primary_location.city if primary_location else None,
        'state': primary_location.state if primary_location else None,
        'primary_location': {
            'practice_name': primary_location.practice_name if primary_location else None,
            'city': primary_location.city if primary_location else None,
            'state': primary_location.state if primary_location else None,
            'street_address': primary_location.street_address if primary_location else None,
            'zip': primary_location.zip if primary_location else None,
        } if primary_location else None,
        'locations': [
            {
                'practice_name': loc.practice_name,
                'street_address': loc.street_address,
                'address_line_2': loc.address_line_2,
                'city': loc.city,
                'state': loc.state,
                'zip': loc.zip,
                'hide_address_from_public': loc.hide_address_from_public,
                'is_primary_address': loc.is_primary_address,
                'office_hours': [
                    {
                        'weekday': oh.weekday,
                        'is_closed': oh.is_closed,
                        'by_appointment_only': oh.by_appointment_only,
                        'start_time_1': oh.start_time_1,
                        'end_time_1': oh.end_time_1,
                        'start_time_2': oh.start_time_2,
                        'end_time_2': oh.end_time_2,
                        'notes': oh.notes,
                    } for oh in loc.office_hours.all()
                ],
            }
            for loc in profile.locations.all()
        ],
        'participant_types': [pt.name for pt in profile.participant_types.all()],
        'age_groups': [ag.name for ag in profile.age_groups.all()],
        'race_ethnicities': [r.race_ethnicity.name for r in profile.race_ethnicities.select_related('race_ethnicity').all()],
        'faiths': [f.faith.name for f in profile.faiths.select_related('faith').all()],
        'lgbtqia_identities': [l.lgbtqia.name for l in profile.lgbtqia_identities.select_related('lgbtqia').all()],
        'other_identities': [o.other_identity.name for o in profile.other_identities.select_related('other_identity').all()],
        'specialties': [
            {
                'name': s.specialty.name if s.specialty else None,
                'is_top': s.is_top_specialty,
            } for s in profile.specialties.select_related('specialty').all()
        ],
        'top_specialties': [s.specialty.name for s in profile.specialties.select_related('specialty').filter(is_top_specialty=True) if s.specialty],
        'therapy_types': [sel.therapy_type.name for sel in profile.types_of_therapy.select_related('therapy_type').all()],
        'other_therapy_types': [o.therapy_type for o in profile.other_therapy_types.all()],
        'areas_of_expertise': [a.expertise for a in profile.areas_of_expertise.all()],
        'accepted_payment_methods': [sel.payment_method.name for sel in profile.accepted_payment_methods.select_related('payment_method').all()],
        'insurance_details': [
            {
                'provider': det.provider.name,
                'out_of_network': det.out_of_network,
            } for det in profile.insurance_details.select_related('provider').all()
        ],
        'gallery_images': [
            {
                'url': img_url(img.image),
                'caption': img.caption,
                'is_primary': img.is_primary,
            }
            for img in profile.gallery_images.all()
            if img_url(img.image)
        ],
        'video_gallery': [
            {
                'video_url': img_url(v.video),
                'caption': v.caption,
            } for v in profile.video_gallery.all()
        ],
        'educations': [
            {
                'school': e.school,
                'degree_diploma': e.degree_diploma,
                'year_graduated': e.year_graduated,
                'year_began_practice': e.year_began_practice,
            } for e in profile.educations.all()
        ],
        'additional_credentials': [
            {
                'type': ac.additional_credential_type,
                'organization_name': ac.organization_name,
                'id_number': ac.id_number,
                'year_issued': ac.year_issued,
            } for ac in profile.additional_credentials.all()
        ],
    }
    return JsonResponse(data, safe=False)

