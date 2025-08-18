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
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from users.utils.profile_completion import compute_profile_completion
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

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
            from django.template.loader import render_to_string
            from django.utils import timezone as _tz
            subject = 'Confirm your email – Therapy Connected'
            ctx = {
                'confirm_url': confirm_url,
                'user_email': email,
                'user_first_name': getattr(user, 'first_name', '') or '',
                'support_email': getattr(settings, 'SUPPORT_EMAIL','support@therapyconnected.com'),
                'year': _tz.now().year,
            }
            plain_text = render_to_string('users/emails/confirm_email.txt', ctx)
            html_body = render_to_string('users/emails/confirm_email.html', ctx)
            success, message_id = service.send_email(
                recipient=email,
                subject=subject,
                plain_text=plain_text,
                html=html_body,
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
                    # Pending payment -> send to payment screen; otherwise land on feed
                    if user.onboarding_status == 'pending_payment':
                        return redirect('payment')
                # Default landing for authenticated users
                return redirect('members_feed')
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
    # Advance guard: already past payment
    if request.user.onboarding_status == 'pending_profile_completion':
        return redirect('edit_profile')
    if request.user.onboarding_status == 'active':
        return redirect('members_feed')

    from users.models import SubscriptionType, Subscription
    selected_plan_id = request.session.get('selected_plan_id')
    selected_plan_interval = request.session.get('selected_plan_interval', 'monthly')
    plans = SubscriptionType.objects.filter(active=True).order_by('price_monthly')

    # Build selected plan summary (for display)
    subscription = None
    if selected_plan_id:
        try:
            plan = SubscriptionType.objects.get(id=selected_plan_id)
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
                'frequency': frequency,
            }
        except SubscriptionType.DoesNotExist:
            pass

    if request.method == 'POST':
        # Collect payment method & customer now, defer actual subscription activation
        payment_method_id = request.POST.get('payment_method_id')
        cardholder = request.POST.get('cardholder') or request.user.email
        user = request.user
        # Create or reuse stripe customer (create new every time for now)
        customer = stripe.Customer.create(email=user.email, name=cardholder)
        # Attach the payment method so it can be used later when we actually create the subscription
        try:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)
        except Exception:
            messages.error(request, 'Unable to attach payment method. Please try again.')
            return redirect('payment')
        sub = Subscription.objects.filter(user=user).last()
        if sub and selected_plan_id:
            try:
                plan = SubscriptionType.objects.get(id=selected_plan_id)
                interval = selected_plan_interval
                sub.subscription_type = plan
                sub.interval = interval
                sub.stripe_customer_id = customer.id
                sub.stripe_payment_method_id = payment_method_id
                # NOTE: stripe_subscription_id intentionally left blank until profile + license validated
                sub.save()
            except SubscriptionType.DoesNotExist:
                pass
        # Advance onboarding but keep user inactive pending profile completion & license validation
        user.onboarding_status = 'pending_profile_completion'
        user.save(update_fields=['onboarding_status'])
        return redirect('edit_profile')

    return render(request, 'users/payment.html', {
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
        'subscription': subscription,
        'plans': plans,
    })

def therapist_profile(request, user_id):
    from users.models_profile import TherapistProfile
    from users.models import TherapistProfileStats
    from django.utils import timezone
    profile = TherapistProfile.objects.filter(user__id=user_id).first()
    if not profile:
        return HttpResponse('Profile not found', status=404)
    # Ensure slug exists (legacy safeguard)
    if not profile.slug:
        profile.save()  # triggers slug generation in model.save
    # Track click (maintain stats parity with old template response)
    today = timezone.now().date()
    stats, _ = TherapistProfileStats.objects.get_or_create(therapist=profile.user, date=today)
    stats.profile_clicks += 1
    stats.save()
    profile.last_viewed_at = timezone.now()
    profile.save(update_fields=['last_viewed_at'])
    # Permanent redirect to canonical slug page
    return redirect('therapist_profile_public_slug', slug=profile.slug)

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
    # Compute approximate distance (miles) from visitor session zip (if set) mirroring search view logic
    profile.distance = None  # default so template condition exists
    user_zip = request.session.get('user_zip')
    if user_zip:
        try:
            import math, re
            from users.models_profile import ZipCode
            user_zip_clean = re.match(r"\d{5}", user_zip or "")
            user_zip_clean = user_zip_clean.group(0) if user_zip_clean else user_zip
            user_zip_row = ZipCode.objects.filter(pk=user_zip_clean).first()
            if user_zip_row:
                # Preload location zip rows to avoid N queries
                loc_zips = {loc.zip for loc in profile.locations.all() if getattr(loc, 'zip', None)}
                zip_rows = {z.zip: z for z in ZipCode.objects.filter(zip__in=loc_zips)}

                def haversine(lat1, lon1, lat2, lon2):
                    R = 3958.8
                    phi1 = math.radians(lat1)
                    phi2 = math.radians(lat2)
                    dphi = math.radians(lat2 - lat1)
                    dlambda = math.radians(lon2 - lon1)
                    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    return R * c

                min_d = None
                for loc in profile.locations.all():
                    zr = zip_rows.get(getattr(loc, 'zip', None))
                    if zr and zr.latitude and zr.longitude:
                        try:
                            d = haversine(float(user_zip_row.latitude), float(user_zip_row.longitude), float(zr.latitude), float(zr.longitude))
                        except Exception:
                            continue
                        if min_d is None or d < min_d:
                            min_d = d
                if min_d is not None:
                    profile.distance = round(min_d, 1)
        except Exception:
            # Swallow errors silently; distance just stays None
            pass
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
    # Explicit override if present & valid
    if getattr(profile, 'year_started_practice', None) and profile.year_started_practice.isdigit() and len(profile.year_started_practice) == 4:
        candidate_years.append(int(profile.year_started_practice))
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
    'middle_name': profile.middle_name,
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
    'receive_calls_from_client': getattr(profile, 'receive_calls_from_client', False),
    'receive_texts_from_clients': getattr(profile, 'receive_texts_from_clients', False),
    'receive_emails_from_clients': getattr(profile, 'receive_emails_from_clients', False),
    'receive_emails_when_client_calls': getattr(profile, 'receive_emails_when_client_calls', False),
        'youtube_url': profile.youtube_url,
        'therapy_types_note': profile.therapy_types_note,
        'specialties_note': profile.specialties_note,
        'license_type': profile.license_type.name if profile.license_type else None,
        'license_type_description': profile.license_type.description if profile.license_type else None,
        'license_type_short': profile.license_type.short_description if profile.license_type else None,
        'license_number': profile.license_number,
        'license_expiration': profile.license_expiration,
        'license_state': profile.license_state,
    'license_first_name': profile.license_first_name,
    'license_last_name': profile.license_last_name,
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
    'distance': profile.distance,
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
    # Normalize any known blocked demo hosts (e.g., samplelib.com) to a permissive sample
    vids = []
    for vg in profile.video_gallery.all():
        try:
            vurl = vg.video.url
        except Exception:
            vurl = None
        if not vurl:
            continue
        # Some public sample hosts block hotlinking and return 403. Replace with a permissive CC0 demo clip.
        if isinstance(vurl, str) and 'samplelib.com/mp4/' in vurl:
            vurl = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
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

@login_required
def edit_profile(request):
    """Render unified edit interface (full public profile layout in edit mode)."""
    from users.models_profile import TherapistProfile
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    # compute completion for initial render (progress bar pre-JS)
    completion = compute_profile_completion(profile)
    import json
    return render(request, 'users/therapist_profile_edit.html', {
        'profile_obj': profile,
        'completion_percent': completion.percent,
        'completion_details': completion.details,
        'initial_profile_json': json.dumps(_profile_json(profile)),
    })

EDITABLE_SIMPLE_FIELDS = {
    'practice_name': str,
    'therapy_delivery_method': str,
    'intro_note': str,
    'personal_statement_01': str,
    'personal_statement_q1': str,
    'personal_statement_q2': str,
    'personal_statement_q3': str,
    'credentials_note': str,
    'finance_note': str,  # allow rich text finance note editing
    'no_show_policy': str,  # allow rich text no-show policy editing
    'therapy_types_note': str,  # newly added rich text field
    'specialties_note': str,    # newly added rich text field
    'year_started_practice': str,  # explicit practice start year
    # accepting_new_clients now tri-state string; allow blank for unset
    'accepting_new_clients': str,
    'first_name': str,
    'last_name': str,
    'middle_name': str,
    'title': str,  # maps to Title.name
    'license_type': str,  # maps to LicenseType.name
    'license_number': str,
    'license_state': str,
    'license_expiration': str,
    'license_first_name': str,
    'license_last_name': str,
    # Contact & Web (strings/booleans)
    'phone_number': str,
    'phone_extension': str,
    'mobile_number': str,
    'office_email': str,
    'practice_website_url': str,
    'facebook_url': str,
    'instagram_url': str,
    'linkedin_url': str,
    'twitter_url': str,
    'tiktok_url': str,
    'youtube_url': str,
    'receive_calls_from_client': bool,
    'receive_texts_from_clients': bool,
    'receive_emails_from_clients': bool,
    'receive_emails_when_client_calls': bool,
}

FIELD_ALIASES = {
    # Support old client field names -> new canonical names
    'intro_statement': 'intro_note',
}
# NOTE: We intentionally do NOT alias 'personal_statement_q1' -> 'personal_statement_01'.
# q1 (guided question response) and personal_statement_01 (long About Me) are distinct.
# Previous alias caused q1 edits to be written into personal_statement_01 and not reflected back.

def _profile_json(profile):
    """Subset JSON for edit context (can expand)."""
    completion = compute_profile_completion(profile)
    # Related collections
    locations = [
        {
            'id': loc.id,
            'practice_name': loc.practice_name,
            'street_address': loc.street_address,
            'address_line_2': loc.address_line_2,
            'city': loc.city,
            'state': loc.state,
            'zip': loc.zip,
            'is_primary_address': getattr(loc, 'is_primary_address', False),
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
        for loc in getattr(profile, 'locations', []).all()
    ]
    # Simple lists
    participant_types = [pt.name for pt in getattr(profile, 'participant_types', []).all()]
    age_groups = [ag.name for ag in getattr(profile, 'age_groups', []).all()]
    specialties = [
        {
            'name': s.specialty.name if s.specialty else None,
            'is_top': getattr(s, 'is_top_specialty', False),
        }
        for s in getattr(profile, 'specialties', []).all()
    ]
    top_specialties = [s['name'] for s in specialties if s['name'] and s['is_top']]
    therapy_types = [sel.therapy_type.name for sel in getattr(profile, 'types_of_therapy', []).all() if getattr(sel, 'therapy_type', None)]
    other_therapy_types = [o.therapy_type for o in getattr(profile, 'other_therapy_types', []).all()]
    race_ethnicities = [r.race_ethnicity.name for r in getattr(profile, 'race_ethnicities', []).all() if getattr(r, 'race_ethnicity', None)]
    faiths = [f.faith.name for f in getattr(profile, 'faiths', []).all() if getattr(f, 'faith', None)]
    lgbtqia_identities = [l.lgbtqia.name for l in getattr(profile, 'lgbtqia_identities', []).all() if getattr(l, 'lgbtqia', None)]
    other_identities = [o.other_identity.name for o in getattr(profile, 'other_identities', []).all() if getattr(o, 'other_identity', None)]
    additional_credentials = [
        {
            'id': ac.id,
            'type': ac.additional_credential_type,
            'organization_name': ac.organization_name,
            'id_number': ac.id_number,
            'year_issued': ac.year_issued,
        }
        for ac in getattr(profile, 'additional_credentials', []).all()
    ]
    educations = [
        {
            'id': e.id,
            'school': e.school,
            'degree_diploma': e.degree_diploma,
            'year_graduated': e.year_graduated,
            'year_began_practice': e.year_began_practice,
        }
        for e in getattr(profile, 'educations', []).all()
    ]
    accepted_payment_methods = [sel.payment_method.name for sel in getattr(profile, 'accepted_payment_methods', []).all() if getattr(sel, 'payment_method', None)]
    areas_of_expertise = [a.expertise for a in getattr(profile, 'areas_of_expertise', []).all()]
    gallery_images = [
        {
            'id': img.id,
            'url': getattr(img.image, 'url', None) if getattr(img, 'image', None) else None,
            'caption': img.caption,
            'is_primary': getattr(img, 'is_primary', False),
        }
        for img in getattr(profile, 'gallery_images', []).all()
        if getattr(getattr(img, 'image', None), 'url', None)
    ]
    # Normalize video URLs to avoid hosts that block hotlinking (403s). Use a permissive CC0 fallback.
    video_gallery = []
    for v in getattr(profile, 'video_gallery', []).all():
        vurl = getattr(v.video, 'url', None) if getattr(v, 'video', None) else None
        if not vurl:
            continue
        if isinstance(vurl, str) and 'samplelib.com/mp4/' in vurl:
            vurl = 'https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4'
        video_gallery.append({
            'video_url': vurl,
            'caption': v.caption,
        })
    # Resolve title & options; license_type options
    from users.models_profile import Title as TitleModel, LicenseType as LicenseTypeModel
    try:
        title_name = profile.title.name if getattr(profile, 'title', None) else None
    except Exception:
        title_name = None
    title_options = list(TitleModel.objects.order_by('name').values_list('name', flat=True))
    # Ensure current title present even if not in list (legacy)
    if title_name and title_name not in title_options:
        title_options.append(title_name)
    # License type options
    license_type_options = list(LicenseTypeModel.objects.order_by('sort_order','name').values_list('name', flat=True))
    current_license = profile.license_type.name if getattr(profile, 'license_type', None) else None
    if current_license and current_license not in license_type_options:
        license_type_options.append(current_license)
    # Race / Ethnicity options
    try:
        from users.models_profile import RaceEthnicity
        race_ethnicity_options = list(RaceEthnicity.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        race_ethnicity_options = []
    # Gender options
    try:
        from users.models_profile import Gender
        gender_options = list(Gender.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        gender_options = []
    # Faith options
    try:
        from users.models_profile import Faith
        faith_options = list(Faith.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        faith_options = []
    # LGBTQIA options
    try:
        from users.models_profile import LGBTQIA
        lgbtqia_options = list(LGBTQIA.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        lgbtqia_options = []
    # Other identity options
    try:
        from users.models_profile import OtherIdentity
        other_identity_options = list(OtherIdentity.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        other_identity_options = []
    data = {
        'id': profile.user_id,
    'onboarding_status': getattr(profile.user, 'onboarding_status', ''),
    'first_name': profile.first_name or getattr(profile.user, 'first_name', ''),
    'middle_name': profile.middle_name or '',
    'last_name': profile.last_name or getattr(profile.user, 'last_name', ''),
    'user_first_name': getattr(profile.user, 'first_name', ''),
    'user_last_name': getattr(profile.user, 'last_name', ''),
    'name': (f"{profile.first_name or getattr(profile.user,'first_name','')} {profile.last_name or getattr(profile.user,'last_name','')}".strip()) or None,
    'title': title_name,
    'year_started_practice': getattr(profile, 'year_started_practice', ''),
    'license_first_name': getattr(profile, 'license_first_name', '') or '',
    'license_last_name': getattr(profile, 'license_last_name', '') or '',
    'gender': profile.gender.name if getattr(profile, 'gender', None) else None,
    'title_options': title_options,
    'license_type_options': license_type_options,
        'practice_name': profile.practice_name,
        'therapy_delivery_method': profile.therapy_delivery_method,
    # Expose new fields; fall back to legacy if new empty
    'intro_note': profile.intro_note or profile.intro_statement or profile.personal_statement_01 or profile.personal_statement_q1,
    # Maintain existing personal_statement_01 (long about) separately; do not auto-fallback to q1 when it's empty (avoid accidental overwrite perception)
    'personal_statement_01': profile.personal_statement_01,
    'personal_statement_q1': profile.personal_statement_q1,
    'personal_statement_q2': profile.personal_statement_q2,
    'personal_statement_q3': profile.personal_statement_q3,
        'credentials_note': profile.credentials_note,
        'finance_note': profile.finance_note,
        'no_show_policy': getattr(profile, 'no_show_policy', ''),
    'therapy_types_note': getattr(profile, 'therapy_types_note', ''),
    'specialties_note': getattr(profile, 'specialties_note', ''),
        'accepting_new_clients': profile.accepting_new_clients,
        'license_type': profile.license_type.name if getattr(profile, 'license_type', None) else None,
        'license_type_short': profile.license_type.short_description if getattr(profile, 'license_type', None) else None,
        'license_type_description': profile.license_type.description if getattr(profile, 'license_type', None) else None,
    # Include raw license entry fields so UI can reflect persisted values
    'license_number': getattr(profile, 'license_number', '') or '',
    'license_state': getattr(profile, 'license_state', '') or '',
    'license_expiration': getattr(profile, 'license_expiration', '') or '',
    'license_first_name': getattr(profile, 'license_first_name', '') or '',
    'license_last_name': getattr(profile, 'license_last_name', '') or '',
    'license_status': getattr(profile, 'license_status', ''),
    'license_last_verified_at': profile.license_last_verified_at.isoformat() if getattr(profile, 'license_last_verified_at', None) else None,
    # Latest license verification message (if any)
    'license_status_message': (lambda _p: (
        __import__('users.models_profile').models_profile.LicenseVerificationLog.objects.filter(therapist=_p).order_by('-created_at').values_list('message', flat=True).first()
    ))(profile),
    # States where automated verification exists (frontend can label others as Manual)
    'license_automated_states': (lambda: list(__import__('users.utils.license_verification').utils.license_verification.STATE_STRATEGIES.keys()))(),
    'race_ethnicity_options': race_ethnicity_options,
    'gender_options': gender_options,
    'faith_options': faith_options,
    'lgbtqia_options': lgbtqia_options,
    'other_identity_options': other_identity_options,
        'profile_photo_url': profile.profile_photo.url if profile.profile_photo else None,
    'locations': locations,
    'gallery_images': gallery_images,
    'video_gallery': video_gallery,
    'participant_types': participant_types,
    'age_groups': age_groups,
    'top_specialties': top_specialties,
    'specialties': specialties,
    'therapy_types': therapy_types,
    'other_therapy_types': other_therapy_types,
    'race_ethnicities': race_ethnicities,
    'faiths': faiths,
    'lgbtqia_identities': lgbtqia_identities,
    'other_identities': other_identities,
    'additional_credentials': additional_credentials,
    'educations': educations,
    'accepted_payment_methods': accepted_payment_methods,
    'areas_of_expertise': areas_of_expertise,
        # Will be appended below: insurance_details
        'completion': {
            'percent': completion.percent,
            'details': completion.details,
        }
    }
    # Insurance details (provider name + out_of_network flag)
    try:
        data['insurance_details'] = [
            {
                'provider': det.provider.name if getattr(det, 'provider', None) else '',
                'out_of_network': getattr(det, 'out_of_network', False),
            } for det in getattr(profile, 'insurance_details', []).all()
        ]
    except Exception:
        data['insurance_details'] = []
    return data

@login_required
@require_http_methods(["GET"])
def api_profile_me(request):
    from users.models_profile import TherapistProfile
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH","POST"])
def api_profile_update(request):
    import json, traceback
    from users.models_profile import TherapistProfile
    try:
        # Fast-path: handle multipart (file upload) POST separately BEFORE touching request.body
        if request.method == 'POST' and request.FILES:
            profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
            f = request.FILES.get('profile_photo') or request.FILES.get('file')
            if not f:
                return JsonResponse({'error': 'No file provided'}, status=400)
            # Basic validations (mirror frontend constraints)
            max_bytes = 5 * 1024 * 1024  # 5MB
            if f.size > max_bytes:
                return JsonResponse({'error': 'File too large (max 5MB)'}, status=400)
            # Basic image signature validation using Pillow (if available)
            kind_valid = True
            try:
                from PIL import Image
                pos = f.tell()
                img = Image.open(f)
                img.verify()  # verifies but does not decode full image
                fmt = (getattr(img, 'format', '') or '').upper()
                if fmt not in {'JPEG','PNG'}:
                    kind_valid = False
                f.seek(pos)
            except Exception:
                kind_valid = False
            if not kind_valid:
                return JsonResponse({'error': 'Unsupported or corrupt image (use JPG or PNG)'}, status=400)
            # Save
            profile.profile_photo = f
            profile.save(update_fields=['profile_photo'])
            return JsonResponse(_profile_json(profile))

        # JSON / PATCH pathway
        try:
            # Avoid RawPostDataException when request already parsed (e.g., multipart) by checking content type
            if request.content_type and request.content_type.startswith('multipart/form-data'):
                payload = {}
            else:
                payload = json.loads(request.body.decode('utf-8')) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error':'Invalid JSON'}, status=400)
        profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
        errors = {}
        updated = False
        # Optional manual re-verification trigger (does not modify fields)
        reverify_requested = bool(payload.get('reverify_license'))
        if 'reverify_license' in payload:
            # Remove to avoid interfering with normal field loop below
            try:
                del payload['reverify_license']
            except KeyError:
                pass
        from users.models_profile import Title as TitleModel
        race_ethnicities_new = faiths_new = lgbtqia_new = other_identities_new = None
        gender_new = None
        insurance_details_new = None  # capture full replacement list
        therapy_types_new = None  # list of therapy type names (full replacement)
        specialties_new = None  # list of specialty names (full replacement)
        top_specialties_new = None  # list of top specialty names (subset of specialties)
        participant_types_new = None  # list of participant type names (full replacement)
        age_groups_new = None  # list of age group names (full replacement)
        license_fields_changed = False
        orig_license_snapshot = {
            'license_type': profile.license_type_id if getattr(profile, 'license_type', None) else None,
            'license_number': profile.license_number,
            'license_state': profile.license_state,
            'license_first_name': profile.license_first_name,
            'license_last_name': profile.license_last_name,
        }
        for field, value in payload.items():
            canonical = FIELD_ALIASES.get(field, field)
            # Special handling: profile photo removal (set to blank string)
            if canonical == 'profile_photo':
                try:
                    if (value or '') == '':
                        if getattr(profile, 'profile_photo', None):
                            try:
                                profile.profile_photo.delete(save=False)
                            except Exception:
                                pass
                        profile.profile_photo = None
                        updated = True
                except Exception:
                    errors['profile_photo'] = 'Failed to remove photo'
                continue
            if canonical in ('race_ethnicities','faiths','lgbtqia_identities','other_identities'):
                if isinstance(value, list):
                    if canonical == 'race_ethnicities': race_ethnicities_new = value
                    elif canonical == 'faiths': faiths_new = value
                    elif canonical == 'lgbtqia_identities': lgbtqia_new = value
                    elif canonical == 'other_identities': other_identities_new = value
                continue
            if canonical == 'gender':
                if isinstance(value, str): gender_new = value
                continue
            if canonical == 'therapy_types':
                if isinstance(value, list): therapy_types_new = value
                continue
            if canonical == 'specialties':
                if isinstance(value, list): specialties_new = value
                continue
            if canonical == 'top_specialties':
                if isinstance(value, list): top_specialties_new = value
                continue
            if canonical == 'insurance_details':
                if isinstance(value, list):
                    insurance_details_new = value
                continue
            if canonical == 'participant_types':
                if isinstance(value, list): participant_types_new = value
                continue
            if canonical == 'age_groups':
                if isinstance(value, list): age_groups_new = value
                continue
            if canonical not in EDITABLE_SIMPLE_FIELDS:
                continue
            # Validations
            if canonical == 'practice_name' and value and len(value) > 120:
                errors[field] = 'Too long (max 120 chars).'; continue
            if canonical in ('first_name','last_name') and value and len(value) > 64:
                errors[field] = 'Too long (max 64 chars).'; continue
            if canonical in ('license_first_name','license_last_name') and value and len(value) > 64:
                errors[field] = 'Too long (max 64 chars).'; continue
            if canonical == 'therapy_delivery_method' and value and value.lower() not in {'in person','online','telehealth','hybrid','in person & online','in-person','in-person & online'}:
                errors[field] = 'Unrecognized delivery method.'; continue
            if canonical in ('personal_statement_01','personal_statement_q1','personal_statement_q2','personal_statement_q3') and value:
                max_len = 1000 if canonical=='personal_statement_01' else 650
                if len(value) > max_len:
                    errors[field] = f'Too long (max {max_len} chars).'; continue
            if canonical == 'credentials_note' and value and len(value) > 600:
                errors[field] = 'Too long (max 600 chars).'; continue
            if canonical == 'license_state' and value:
                val = (value or '').strip().upper()
                if len(val) != 2 or not val.isalpha():
                    errors[field] = 'Use 2-letter state code.'; continue
                value = val
            if canonical == 'license_expiration' and value:
                import re
                raw = value.strip().replace('-', '/').replace(' ', '')
                # Accept M/YYYY or MM/YYYY where month 1-12; always normalize to MM/YYYY
                m = re.match(r'^([0]?[1-9]|1[0-2])/(20\d\d)$', raw)
                if not m:
                    errors[field] = 'Use MM/YYYY (e.g., 08/2026)'; continue
                month = m.group(1)
                if len(month) == 1:
                    month = '0' + month
                value = f"{month}/{m.group(2)}"
            if canonical == 'license_number' and value:
                if len(value) > 32:
                    errors[field] = 'Too long (max 32 chars).'; continue
                # Allow duplicates across profiles (state + number not enforced). Any future
                # dedup / conflict resolution will occur during verification logic instead.
            if canonical == 'accepting_new_clients':
                normalized = ''
                if isinstance(value, bool):
                    normalized = 'Accepting New Clients' if value else 'Not Accepting New Clients'
                else:
                    raw = (value or '').strip().lower()
                    if raw in {'yes','y','accepting','accepting new clients','open','true'}: normalized='Accepting New Clients'
                    elif raw in {'no','n','not accepting','not accepting new clients','closed','false'}: normalized='Not Accepting New Clients'
                    elif 'wait' in raw: normalized='I Have a Waitlist'
                    elif raw == '': normalized=''
                    else:
                        errors[field]='Invalid availability value.'; continue
                value = normalized
            if canonical == 'title':
                if value:
                    if len(value) > 16: errors[field]='Too long (max 16 chars).'; continue
                    t_obj = TitleModel.objects.filter(name__iexact=value.strip()).first()
                    if not t_obj: errors[field]='Invalid title selection.'; continue
                    profile.title = t_obj
                else:
                    profile.title = None
                updated = True; continue
            if canonical == 'license_type':
                if value:
                    if len(value) > 64: errors[field]='Too long (max 64 chars).'; continue
                    from users.models_profile import LicenseType as LicenseTypeModel
                    lt_obj = LicenseTypeModel.objects.filter(name__iexact=value.strip()).first()
                    if not lt_obj: errors[field]='Invalid license type selection.'; continue
                    profile.license_type = lt_obj
                else:
                    profile.license_type = None
                updated = True; license_fields_changed = True; continue
            setattr(profile, canonical, value); updated = True
            if canonical in {'license_number','license_state','license_first_name','license_last_name'}:
                license_fields_changed = True
        # Multi-select helpers
        def process_multi(new_vals, rel_attr, model_cls_name, sel_cls_name, field_name, error_key):
            """Generic full-replace handler for identity-style multi selects.
            Accepts list of strings OR list of objects with a 'name' key.
            Automatically creates new lookup records for unknown values instead of 400-ing.
            Limits to 50 unique values (then truncates)."""
            if new_vals is None or error_key in errors:
                return
            from users import models_profile as mp
            try:
                model_cls = getattr(mp, model_cls_name)
                sel_cls = getattr(mp, sel_cls_name)
                # Build map of existing names
                existing_map = {r.name.lower(): r for r in model_cls.objects.all()}
                cleaned=[]; seen=set()
                for item in new_vals:
                    if isinstance(item, dict):
                        val = (item.get('name') or '').strip()
                    else:
                        val = (str(item) if isinstance(item, str) else '').strip()
                    if not val:
                        continue
                    key = val.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    # Enforce length constraint defensively
                    if len(val) > 64:
                        val = val[:64]
                    # Create lookup if missing (dynamic extend)
                    obj = existing_map.get(key)
                    if not obj:
                        obj = model_cls.objects.create(name=val)
                        existing_map[key] = obj
                    cleaned.append(obj)
                    if len(cleaned) >= 50:
                        break
                # Replace selections
                from django.db import transaction as _tx
                with _tx.atomic():
                    getattr(profile, rel_attr).all().delete()
                    for obj in cleaned[:12]:  # preserve previous 12-item cap
                        sel_cls.objects.create(therapist=profile, **{field_name: obj})
                nonlocal updated
                updated = True
            except Exception:
                errors[error_key] = f"Failed to update {field_name.replace('_', ' ')}"
        process_multi(race_ethnicities_new,'race_ethnicities','RaceEthnicity','RaceEthnicitySelection','race_ethnicity','race_ethnicities')
        process_multi(faiths_new,'faiths','Faith','FaithSelection','faith','faiths')
        process_multi(lgbtqia_new,'lgbtqia_identities','LGBTQIA','LGBTQIASelection','lgbtqia','lgbtqia_identities')
        process_multi(other_identities_new,'other_identities','OtherIdentity','OtherIdentitySelection','other_identity','other_identities')
        # Gender single
        if gender_new is not None and 'gender' not in errors:
            try:
                from users.models_profile import Gender
                if gender_new.strip()==''[0:]:
                    profile.gender=None; updated=True
                else:
                    g = Gender.objects.filter(name__iexact=gender_new.strip()).first()
                    if not g: errors['gender']='Unknown gender selection'
                    else: profile.gender=g; updated=True
            except Exception:
                errors['gender']='Failed to update gender'
    # Insurance details full replace (list of {provider, out_of_network})
        if insurance_details_new is not None and 'insurance_details' not in errors:
            try:
                from users.models_profile import InsuranceProvider, InsuranceDetail
                # Normalize entries
                cleaned = []
                seen = set()
                for item in insurance_details_new:
                    if not isinstance(item, dict):
                        continue
                    name = (item.get('provider') or '').strip()
                    if not name:
                        continue
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    if len(name) > 256:
                        name = name[:256]
                    oon = bool(item.get('out_of_network'))
                    cleaned.append({'name': name, 'out_of_network': oon})
                if len(cleaned) > 40:
                    errors['insurance_details'] = 'Too many providers (max 40).'
                if 'insurance_details' not in errors:
                    # Fetch existing providers map (case-insensitive)
                    existing = {p.name.lower(): p for p in InsuranceProvider.objects.all()}
                    provider_objs = []
                    for it in cleaned:
                        p = existing.get(it['name'].lower())
                        if not p:
                            # Create new provider
                            p = InsuranceProvider.objects.create(name=it['name'])
                            existing[p.name.lower()] = p
                        provider_objs.append((p, it['out_of_network']))
                    # Replace InsuranceDetail set
                    from django.db import transaction
                    with transaction.atomic():
                        profile.insurance_details.all().delete()
                        for prov, oon in provider_objs:
                            InsuranceDetail.objects.create(therapist=profile, provider=prov, out_of_network=oon)
                    updated = True
            except Exception as ex:
                errors['insurance_details'] = 'Failed to update insurance details'
        # Therapy Types full replacement
        if therapy_types_new is not None and 'therapy_types' not in errors:
            try:
                from users.models_profile import TherapyType, TherapyTypeSelection
                cleaned=[]; seen=set()
                for name in therapy_types_new:
                    if not isinstance(name, str): continue
                    nm=name.strip()
                    if not nm: continue
                    key=nm.lower()
                    if key in seen: continue
                    seen.add(key)
                    if len(nm)>64: nm=nm[:64]
                    cleaned.append(nm)
                if len(cleaned) > 60:
                    errors['therapy_types'] = 'Too many therapy types (max 60).'
                if 'therapy_types' not in errors:
                    existing = {t.name.lower(): t for t in TherapyType.objects.all()}
                    objs=[]
                    for nm in cleaned:
                        obj = existing.get(nm.lower())
                        if not obj:
                            obj = TherapyType.objects.create(name=nm)
                            existing[obj.name.lower()] = obj
                        objs.append(obj)
                    from django.db import transaction as _tx
                    with _tx.atomic():
                        profile.types_of_therapy.all().delete()
                        for obj in objs:
                            TherapyTypeSelection.objects.create(therapist=profile, therapy_type=obj)
                    updated = True
            except Exception:
                errors['therapy_types'] = 'Failed to update therapy types'
        # Specialties full replacement (with top specialties subset)
        if (specialties_new is not None or top_specialties_new is not None) and 'specialties' not in errors and 'top_specialties' not in errors:
            try:
                from users.models_profile import SpecialtyLookup, Specialty
                # If only updating tops, keep current specialties list
                current_list = [s.specialty.name for s in profile.specialties.select_related('specialty').all() if s.specialty]
                spec_source = specialties_new if specialties_new is not None else current_list
                top_source = top_specialties_new if top_specialties_new is not None else [s.specialty.name for s in profile.specialties.filter(is_top_specialty=True).select_related('specialty').all() if s.specialty]
                cleaned=[]; seen=set()
                for name in spec_source or []:
                    if not isinstance(name, str): continue
                    nm=name.strip()
                    if not nm: continue
                    key=nm.lower();
                    if key in seen: continue
                    seen.add(key)
                    if len(nm)>64: nm=nm[:64]
                    cleaned.append(nm)
                top_cleaned=[]; top_seen=set()
                for name in top_source or []:
                    if not isinstance(name, str): continue
                    nm=name.strip()
                    if not nm: continue
                    key=nm.lower();
                    if key in top_seen: continue
                    top_seen.add(key)
                    if len(nm)>64: nm=nm[:64]
                    top_cleaned.append(nm)
                if any(t.lower() not in {c.lower() for c in cleaned} for t in top_cleaned):
                    errors['top_specialties'] = 'Top specialties must be in specialties list.'
                if len(top_cleaned) > 5:
                    errors['top_specialties'] = 'You can only mark up to 5 top specialties.'
                if 'specialties' not in errors and 'top_specialties' not in errors:
                    # create lookups as needed
                    existing = {s.name.lower(): s for s in SpecialtyLookup.objects.all()}
                    lookups=[]
                    for nm in cleaned:
                        obj = existing.get(nm.lower())
                        if not obj:
                            obj = SpecialtyLookup.objects.create(name=nm)
                            existing[obj.name.lower()] = obj
                        lookups.append(obj)
                    top_set = {t.lower() for t in top_cleaned}
                    from django.db import transaction as _tx
                    with _tx.atomic():
                        profile.specialties.all().delete()
                        for obj in lookups:
                            profile.specialties.create(specialty=obj, is_top_specialty=(obj.name.lower() in top_set))
                    updated = True
            except Exception:
                errors['specialties'] = 'Failed to update specialties'
        # Participant Types full replacement (direct M2M)
        if participant_types_new is not None and 'participant_types' not in errors:
            try:
                from users.models_profile import ParticipantType
                cleaned=[]; seen=set()
                for name in participant_types_new:
                    if not isinstance(name, str): continue
                    nm=name.strip()
                    if not nm: continue
                    key=nm.lower()
                    if key in seen: continue
                    seen.add(key)
                    if len(nm)>32: nm=nm[:32]
                    cleaned.append(nm)
                if len(cleaned) > 40:
                    errors['participant_types'] = 'Too many participant types (max 40).'
                if 'participant_types' not in errors:
                    existing = {p.name.lower(): p for p in ParticipantType.objects.all()}
                    objs=[]
                    for nm in cleaned:
                        obj = existing.get(nm.lower())
                        if not obj:
                            obj = ParticipantType.objects.create(name=nm)
                            existing[obj.name.lower()] = obj
                        objs.append(obj)
                    profile.participant_types.set(objs)
                    updated = True
            except Exception:
                errors['participant_types'] = 'Failed to update participant types'
        # Age Groups full replacement (direct M2M)
        if age_groups_new is not None and 'age_groups' not in errors:
            try:
                from users.models_profile import AgeGroup
                cleaned=[]; seen=set()
                for name in age_groups_new:
                    if not isinstance(name, str): continue
                    nm=name.strip()
                    if not nm: continue
                    key=nm.lower()
                    if key in seen: continue
                    seen.add(key)
                    if len(nm)>32: nm=nm[:32]
                    cleaned.append(nm)
                if len(cleaned) > 40:
                    errors['age_groups'] = 'Too many age groups (max 40).'
                if 'age_groups' not in errors:
                    existing = {a.name.lower(): a for a in AgeGroup.objects.all()}
                    objs=[]
                    for nm in cleaned:
                        obj = existing.get(nm.lower())
                        if not obj:
                            obj = AgeGroup.objects.create(name=nm)
                            existing[obj.name.lower()] = obj
                        objs.append(obj)
                    profile.age_groups.set(objs)
                    updated = True
            except Exception:
                errors['age_groups'] = 'Failed to update age groups'
        if errors:
            # Helpful debug echo of attempted fields (excluding potential large text) for frontend troubleshooting
            debug_fields = list(payload.keys())[:40]
            return JsonResponse({'errors': errors, 'attempted_fields': debug_fields}, status=400)
        if updated:
            # Use db_transaction alias to avoid any accidental shadowing
            with db_transaction.atomic():
                profile.save()
            # Attempt deferred subscription activation (license + minimal profile requirements)
            try:
                _attempt_subscription_activation(request.user)
            except Exception:
                # Silently ignore activation errors; user can continue editing
                pass
            # Trigger license verification if relevant fields changed
            if license_fields_changed or reverify_requested:
                try:
                    # Run asynchronously so UI can show immediate 'pending' status
                    if profile.license_number and profile.license_state and profile.license_type:
                        # Only reset to pending if we are changing license fields OR status not already pending OR reverify explicitly requested
                        if license_fields_changed or reverify_requested or profile.license_status != 'pending':
                            profile.license_status = 'pending'
                            profile.license_last_verified_at = None
                            profile.license_verification_source_url = ''
                            profile.license_verification_raw = {}
                            profile.save(update_fields=['license_status','license_last_verified_at','license_verification_source_url','license_verification_raw'])
                        def _bg_verify(pid):
                            try:
                                from users.utils.license_verification import verify_and_persist
                                from users.models_profile import TherapistProfile as _TP
                                p = _TP.objects.filter(pk=pid).first()
                                if p:
                                    verify_and_persist(p)
                            except Exception:
                                # If background thread errors, mark as error so UI doesn't spin forever
                                try:
                                    from users.models_profile import TherapistProfile as _TP2
                                    p2 = _TP2.objects.filter(pk=pid).first()
                                    if p2 and p2.license_status == 'pending':
                                        p2.license_status = 'error'
                                        p2.save(update_fields=['license_status'])
                                except Exception:
                                    pass
                        def _bg_timeout(pid):
                            # Safety: if still pending after 70s, mark timeout error
                            import time
                            time.sleep(70)
                            try:
                                from users.models_profile import TherapistProfile as _TP3
                                p3 = _TP3.objects.filter(pk=pid).first()
                                if p3 and p3.license_status == 'pending' and p3.license_last_verified_at is None:
                                    p3.license_status = 'error'
                                    # store simple timeout message if field exists
                                    try:
                                        p3.license_verification_source_url = (p3.license_verification_source_url or '')
                                    except Exception:
                                        pass
                                    p3.save(update_fields=['license_status','license_verification_source_url'])
                            except Exception:
                                pass
                        import threading as _th
                        _th.Thread(target=_bg_verify, args=(profile.pk,), daemon=True).start()
                        _th.Thread(target=_bg_timeout, args=(profile.pk,), daemon=True).start()
                    else:
                        # License fields incomplete/cleared: reset status to unverified
                        profile.license_status = 'unverified'
                        profile.license_last_verified_at = None
                        profile.license_verification_source_url = ''
                        profile.license_verification_raw = {}
                        profile.save(update_fields=['license_status','license_last_verified_at','license_verification_source_url','license_verification_raw'])
                except Exception:
                    # swallow background scheduling errors
                    pass
        return JsonResponse(_profile_json(profile))
    except Exception as ex:
        traceback.print_exc()
        return JsonResponse({'error':'Server error','detail':str(ex)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_insurance_providers(request):
    """Lookup insurance providers with optional fuzzy name search (?q=...).
    Returns list of {id,name}. Limits to 20 results."""
    from users.models_profile import InsuranceProvider
    q = (request.GET.get('q') or '').strip()
    qs = InsuranceProvider.objects.all().order_by('sort_order','name')
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{'id': p.id, 'name': p.name} for p in qs[:20]]
    return JsonResponse({'results': data})

@login_required
@require_http_methods(["GET"])
def api_therapy_types(request):
    """Lookup therapy types (?q=) limit 20."""
    from users.models_profile import TherapyType
    q = (request.GET.get('q') or '').strip()
    qs = TherapyType.objects.all().order_by('sort_order','name')
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{'id': t.id, 'name': t.name} for t in qs[:20]]
    return JsonResponse({'results': data})

@login_required
@require_http_methods(["GET"])
def api_specialties_lookup(request):
    """Lookup specialties (?q=) limit 20."""
    from users.models_profile import SpecialtyLookup
    q = (request.GET.get('q') or '').strip()
    qs = SpecialtyLookup.objects.all().order_by('sort_order','name')
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{'id': s.id, 'name': s.name} for s in qs[:20]]
    return JsonResponse({'results': data})

@login_required
@require_http_methods(["GET"])
def api_participant_types(request):
    """Lookup participant types (?q=) limit 20."""
    from users.models_profile import ParticipantType
    q = (request.GET.get('q') or '').strip()
    qs = ParticipantType.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{'id': p.id, 'name': p.name} for p in qs[:20]]
    return JsonResponse({'results': data})

@login_required
@require_http_methods(["GET"])
def api_age_groups(request):
    """Lookup age groups (?q=) limit 20."""
    from users.models_profile import AgeGroup
    q = (request.GET.get('q') or '').strip()
    qs = AgeGroup.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    data = [{'id': a.id, 'name': a.name} for a in qs[:20]]
    return JsonResponse({'results': data})

@login_required
@require_http_methods(["POST"])
def api_profile_submit(request):
    """Submit profile for activation. Validates minimum completion and triggers
    deferred subscription activation, then returns a redirect to the dashboard.

    Always redirects to dashboard on success so users can proceed even if
    activation remains pending (e.g., license verification outstanding).
    """
    from users.models_profile import TherapistProfile
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    # Server-side minimal completion check
    result = compute_profile_completion(profile)
    if result.percent < 100:
        return JsonResponse({'error': 'Minimum profile requirements not met', 'percent': result.percent}, status=400)
    # Attempt activation (may be a no-op if prerequisites aren\'t met yet)
    try:
        _attempt_subscription_activation(request.user)
    except Exception:
        pass
    # Return current onboarding_status and dashboard redirect
    return JsonResponse({'success': True, 'onboarding_status': getattr(request.user, 'onboarding_status', ''), 'redirect': reverse('members_feed')})

@login_required
@require_http_methods(["POST", "DELETE"])
def api_profile_upload_photo(request):
    from users.models_profile import TherapistProfile
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    if request.method == 'DELETE':
        # Clear existing photo
        try:
            if profile.profile_photo:
                # Delete file from storage but ignore errors silently
                try:
                    profile.profile_photo.delete(save=False)
                except Exception:
                    pass
            profile.profile_photo = None
            profile.save()
        except Exception:
            return JsonResponse({'error': 'Unable to remove photo'}, status=500)
        return JsonResponse(_profile_json(profile))
    # POST (upload)
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    if file.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (max 5MB).'}, status=400)
    if not file.content_type.lower().startswith(('image/')):
        return JsonResponse({'error': 'Unsupported file type'}, status=400)
    profile.profile_photo = file
    profile.save()
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["POST"])
def api_education_create(request):
    """Create a new education record. JSON body: {school, degree_diploma, year_graduated, year_began_practice?}"""
    import json
    from users.models_profile import TherapistProfile, Education
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    school = (payload.get('school') or '').strip()[:64]
    degree = (payload.get('degree_diploma') or '').strip()[:32]
    year_grad = (payload.get('year_graduated') or '').strip()[:4]
    year_begin = (payload.get('year_began_practice') or '').strip()[:4]
    if not school or not degree or not year_grad:
        return JsonResponse({'error':'school, degree_diploma, year_graduated required'}, status=400)
    try:
        Education.objects.create(therapist=profile, school=school, degree_diploma=degree, year_graduated=year_grad, year_began_practice=year_begin)
    except Exception as ex:
        return JsonResponse({'error':'Create failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH","DELETE"])
def api_education_item(request, education_id):
    """Update or delete an education record."""
    import json
    from users.models_profile import TherapistProfile, Education
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    edu = Education.objects.filter(id=education_id, therapist=profile).first()
    if not edu:
        return JsonResponse({'error':'Education not found'}, status=404)
    if request.method == 'DELETE':
        try:
            edu.delete()
        except Exception:
            return JsonResponse({'error':'Delete failed'}, status=500)
        return JsonResponse(_profile_json(profile))
    # PATCH
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    changed=False
    if 'school' in payload:
        edu.school = (payload.get('school') or '').strip()[:64]; changed=True
    if 'degree_diploma' in payload:
        edu.degree_diploma = (payload.get('degree_diploma') or '').strip()[:32]; changed=True
    if 'year_graduated' in payload:
        edu.year_graduated = (payload.get('year_graduated') or '').strip()[:4]; changed=True
    if 'year_began_practice' in payload:
        edu.year_began_practice = (payload.get('year_began_practice') or '').strip()[:4]; changed=True
    if changed:
        try:
            edu.save()
        except Exception as ex:
            return JsonResponse({'error':'Update failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["POST"])
def api_additional_credential_create(request):
    """Create an additional credential. JSON: {type, organization_name, id_number?, year_issued}"""
    import json
    from users.models_profile import TherapistProfile, AdditionalCredential
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    ctype = (payload.get('type') or '').strip()[:16]
    org = (payload.get('organization_name') or '').strip()[:64]
    idnum = (payload.get('id_number') or '').strip()[:32]
    year = (payload.get('year_issued') or '').strip()[:4]
    if not org or not year:
        return JsonResponse({'error':'organization_name and year_issued required'}, status=400)
    try:
        AdditionalCredential.objects.create(therapist=profile, additional_credential_type=ctype, organization_name=org, id_number=idnum, year_issued=year)
    except Exception as ex:
        return JsonResponse({'error':'Create failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH","DELETE"])
def api_additional_credential_item(request, credential_id):
    """Update or delete an additional credential."""
    import json
    from users.models_profile import TherapistProfile, AdditionalCredential
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    cred = AdditionalCredential.objects.filter(id=credential_id, therapist=profile).first()
    if not cred:
        return JsonResponse({'error':'Credential not found'}, status=404)
    if request.method == 'DELETE':
        try:
            cred.delete()
        except Exception:
            return JsonResponse({'error':'Delete failed'}, status=500)
        return JsonResponse(_profile_json(profile))
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    changed=False
    if 'type' in payload:
        cred.additional_credential_type = (payload.get('type') or '').strip()[:16]; changed=True
    if 'organization_name' in payload:
        cred.organization_name = (payload.get('organization_name') or '').strip()[:64]; changed=True
    if 'id_number' in payload:
        cred.id_number = (payload.get('id_number') or '').strip()[:32]; changed=True
    if 'year_issued' in payload:
        cred.year_issued = (payload.get('year_issued') or '').strip()[:4]; changed=True
    if changed:
        try:
            cred.save()
        except Exception as ex:
            return JsonResponse({'error':'Update failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["POST"])
def api_profile_gallery_upload(request):
    """Upload a gallery image (multipart form: file, optional caption, optional is_primary)."""
    from users.models_profile import TherapistProfile, GalleryImage
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)
    if file.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (max 5MB).'}, status=400)
    if not file.content_type.lower().startswith(('image/')):
        return JsonResponse({'error': 'Unsupported file type'}, status=400)
    caption = request.POST.get('caption','')[:128]
    is_primary = request.POST.get('is_primary','').lower() in {'1','true','yes','on'}
    try:
        gi = GalleryImage.objects.create(therapist=profile, image=file, caption=caption, is_primary=is_primary)
        if is_primary:
            # ensure others set to false
            GalleryImage.objects.filter(therapist=profile).exclude(id=gi.id).update(is_primary=False)
    except Exception as ex:
        return JsonResponse({'error':'Upload failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH","DELETE"])
def api_profile_gallery_item(request, image_id):
    """Update caption / primary flag (PATCH) or delete image (DELETE)."""
    import json
    from users.models_profile import TherapistProfile, GalleryImage
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    gi = GalleryImage.objects.filter(id=image_id, therapist=profile).first()
    if not gi:
        return JsonResponse({'error':'Image not found'}, status=404)
    if request.method == 'DELETE':
        try:
            gi.delete()
        except Exception:
            return JsonResponse({'error':'Unable to delete image'}, status=500)
        return JsonResponse(_profile_json(profile))
    # PATCH
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    changed = False
    if 'caption' in payload:
        cap = (payload.get('caption') or '')[:128]
        gi.caption = cap; changed=True
    if 'is_primary' in payload:
        val = bool(payload.get('is_primary'))
        gi.is_primary = val; changed=True
        if val:
            from users.models_profile import GalleryImage as GI
            GI.objects.filter(therapist=profile).exclude(id=gi.id).update(is_primary=False)
    if changed:
        gi.save()
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["POST","PATCH","DELETE"])
def api_profile_video(request):
    """Manage single therapist intro video.
    POST: multipart upload (file, optional caption) replaces any existing video.
    PATCH: JSON {caption:"..."} updates caption.
    DELETE: removes existing video.

    Size limit: 60MB. Accepts content_type starting with 'video/'.
    """
    from users.models_profile import TherapistProfile, VideoGallery
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    existing = VideoGallery.objects.filter(therapist=profile).first()
    if request.method == 'DELETE':
        if existing:
            try:
                existing.delete()
            except Exception:
                return JsonResponse({'error':'Unable to delete video'}, status=500)
        return JsonResponse(_profile_json(profile))
    if request.method == 'PATCH':
        import json
        if not existing:
            return JsonResponse({'error':'No video to update'}, status=404)
        try:
            payload = json.loads(request.body.decode('utf-8')) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error':'Invalid JSON'}, status=400)
        if 'caption' in payload:
            existing.caption = (payload.get('caption') or '')[:128]
            existing.save()
        return JsonResponse(_profile_json(profile))
    # POST (upload/replace)
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error':'No file uploaded'}, status=400)
    if file.size > 60 * 1024 * 1024:
        return JsonResponse({'error':'File too large (max 60MB).'}, status=400)
    if not file.content_type.lower().startswith('video/'):
        return JsonResponse({'error':'Unsupported file type'}, status=400)
    caption = (request.POST.get('caption','')[:128])
    # Replace existing
    if existing:
        try:
            existing.delete()
        except Exception:
            pass
    try:
        VideoGallery.objects.create(therapist=profile, video=file, caption=caption)
    except Exception as ex:
        return JsonResponse({'error':'Upload failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["POST"])
def api_location_create(request):
    from users.models_profile import TherapistProfile, Location
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    practice_name = (request.POST.get('practice_name','') or '')[:128]
    city = (request.POST.get('city','') or '')[:64]
    state = (request.POST.get('state','') or '')[:32]
    street_address = (request.POST.get('street_address','') or '')[:128]
    address_line_2 = (request.POST.get('address_line_2','') or '')[:128]
    zip_code = (request.POST.get('zip','') or '')[:16]
    is_primary = request.POST.get('is_primary_address','').lower() in {'1','true','yes','on'}
    try:
        loc = Location.objects.create(
            therapist=profile,
            practice_name=practice_name,
            city=city,
            state=state,
            street_address=street_address,
            address_line_2=address_line_2,
            zip=zip_code,
            is_primary_address=is_primary,
        )
        if is_primary:
            Location.objects.filter(therapist=profile).exclude(id=loc.id).update(is_primary_address=False)
    except Exception as ex:
        return JsonResponse({'error':'Create failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH","DELETE"])
def api_location_item(request, location_id):
    import json
    from users.models_profile import TherapistProfile, Location
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    loc = Location.objects.filter(id=location_id, therapist=profile).first()
    if not loc:
        return JsonResponse({'error':'Location not found'}, status=404)
    if request.method == 'DELETE':
        try:
            loc.delete()
        except Exception:
            return JsonResponse({'error':'Unable to delete'}, status=500)
        return JsonResponse(_profile_json(profile))
    # PATCH
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    fields = ['practice_name','street_address','address_line_2','city','state','zip']
    for f in fields:
        if f in payload:
            val = (payload.get(f) or '')
            setattr(loc, f if f!='zip' else 'zip', val[:128])
    if 'is_primary_address' in payload:
        val = bool(payload.get('is_primary_address'))
        loc.is_primary_address = val
    try:
        loc.save()
        if loc.is_primary_address:
            Location.objects.filter(therapist=profile).exclude(id=loc.id).update(is_primary_address=False)
    except Exception as ex:
        return JsonResponse({'error':'Update failed','detail':str(ex)}, status=500)
    return JsonResponse(_profile_json(profile))

@login_required
@require_http_methods(["PATCH"])
def api_location_office_hours(request, location_id):
    """Upsert all office hours rows (0-6) for a location.
    Expects JSON: {"office_hours": [{weekday:int, is_closed:bool, by_appointment_only:bool, start_time_1, end_time_1, start_time_2, end_time_2, notes}]}
    Missing weekdays are left unchanged (client should normally send all 0..6)."""
    import json, re
    from users.models_profile import TherapistProfile, Location, OfficeHour
    profile, _ = TherapistProfile.objects.get_or_create(user=request.user)
    loc = Location.objects.filter(id=location_id, therapist=profile).first()
    if not loc:
        return JsonResponse({'error':'Location not found'}, status=404)
    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error':'Invalid JSON'}, status=400)
    items = payload.get('office_hours', []) or []
    # Index by weekday for quick access
    by_day = {int(it.get('weekday')): it for it in items if 'weekday' in it}
    time_re = re.compile(r'^\d{2}:\d{2}$')
    for wd in sorted(by_day.keys()):
        if wd < 0 or wd > 6:
            return JsonResponse({'error': f'Invalid weekday {wd}'}, status=400)
        data = by_day[wd]
        is_closed = bool(data.get('is_closed'))
        by_appt = bool(data.get('by_appointment_only'))
        def clean_time(val):
            if not val:
                return ''
            val = str(val)[:5]
            return val if time_re.match(val) else ''
        start_time_1 = clean_time(data.get('start_time_1')) if not (is_closed or by_appt) else ''
        end_time_1 = clean_time(data.get('end_time_1')) if not (is_closed or by_appt) else ''
        start_time_2 = clean_time(data.get('start_time_2')) if not (is_closed or by_appt) else ''
        end_time_2 = clean_time(data.get('end_time_2')) if not (is_closed or by_appt) else ''
        notes = (data.get('notes') or '')[:64]
        oh, _ = OfficeHour.objects.get_or_create(location=loc, weekday=wd)
        oh.is_closed = is_closed
        oh.by_appointment_only = by_appt
        oh.start_time_1 = start_time_1
        oh.end_time_1 = end_time_1
        oh.start_time_2 = start_time_2
        oh.end_time_2 = end_time_2
        oh.notes = notes
        try:
            oh.save()
        except Exception as ex:
            return JsonResponse({'error':'Save failed','detail':str(ex),'weekday':wd}, status=500)
    return JsonResponse(_profile_json(profile))

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
    Title as TitleModel,
    )
    from django.utils import timezone
    profile = get_object_or_404(
        TherapistProfile.objects.select_related('license_type', 'gender', 'title', 'user')
        .prefetch_related('locations__office_hours'),
        user__id=user_id
    )
    # Compute approximate distance (miles) from session user_zip if present
    distance_value = None
    user_zip = request.session.get('user_zip')
    if user_zip:
        try:
            import math, re
            from users.models_profile import ZipCode
            user_zip_clean = re.match(r"\d{5}", user_zip or "")
            user_zip_clean = user_zip_clean.group(0) if user_zip_clean else user_zip
            user_zip_row = ZipCode.objects.filter(pk=user_zip_clean).first()
            if user_zip_row:
                loc_zips = {loc.zip for loc in profile.locations.all() if getattr(loc, 'zip', None)}
                zip_rows = {z.zip: z for z in ZipCode.objects.filter(zip__in=loc_zips)}
                def haversine(lat1, lon1, lat2, lon2):
                    R = 3958.8
                    phi1 = math.radians(lat1)
                    phi2 = math.radians(lat2)
                    dphi = math.radians(lat2 - lat1)
                    dlambda = math.radians(lon2 - lon1)
                    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    return R * c
                min_d = None
                for loc in profile.locations.all():
                    zr = zip_rows.get(getattr(loc, 'zip', None))
                    if zr and zr.latitude and zr.longitude:
                        try:
                            d = haversine(float(user_zip_row.latitude), float(user_zip_row.longitude), float(zr.latitude), float(zr.longitude))
                        except Exception:
                            continue
                        if min_d is None or d < min_d:
                            min_d = d
                if min_d is not None:
                    distance_value = round(min_d, 1)
        except Exception:
            pass
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
    if getattr(profile, 'year_started_practice', None) and profile.year_started_practice.isdigit() and len(profile.year_started_practice) == 4:
        candidate_years.append(int(profile.year_started_practice))
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
        'no_show_policy': getattr(profile, 'no_show_policy', ''),
        'credentials_note': profile.credentials_note,
        'profile_photo_url': profile.profile_photo.url if profile.profile_photo else None,
    'title_options': list(TitleModel.objects.order_by('name').values_list('name', flat=True)),
    'practice_website_url': profile.practice_website_url,
        'facebook_url': profile.facebook_url,
        'instagram_url': profile.instagram_url,
        'linkedin_url': profile.linkedin_url,
        'twitter_url': profile.twitter_url,
        'tiktok_url': profile.tiktok_url,
    'youtube_url': profile.youtube_url,
    # Contact preferences (booleans)
    'receive_calls_from_client': getattr(profile, 'receive_calls_from_client', False),
    'receive_texts_from_clients': getattr(profile, 'receive_texts_from_clients', False),
    'receive_emails_from_clients': getattr(profile, 'receive_emails_from_clients', False),
    'receive_emails_when_client_calls': getattr(profile, 'receive_emails_when_client_calls', False),
        'therapy_types_note': profile.therapy_types_note,
        'specialties_note': profile.specialties_note,
        'license_type': profile.license_type.name if profile.license_type else None,
        'license_type_description': profile.license_type.description if profile.license_type else None,
    'license_type_short': profile.license_type.short_description if profile.license_type else None,
        'license_number': profile.license_number,
        'license_expiration': profile.license_expiration,
        'license_state': profile.license_state,
    'license_first_name': profile.license_first_name,
    'license_last_name': profile.license_last_name,
        'gender': profile.gender.name if profile.gender else None,
    'years_in_practice': years_in_practice,
    'year_started_practice': getattr(profile, 'year_started_practice', ''),
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
    # Option lists (identity) for potential client-side editors
    'gender_options': [],
    'faith_options': [],
    'lgbtqia_options': [],
    'other_identity_options': [],
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
    'distance': distance_value,
    }
    # Populate identity option lists (avoid large duplication if not needed)
    try:
        from users.models_profile import Gender, Faith, LGBTQIA, OtherIdentity
        data['gender_options'] = list(Gender.objects.order_by('name').values_list('name', flat=True))
        data['faith_options'] = list(Faith.objects.order_by('name').values_list('name', flat=True))
        data['lgbtqia_options'] = list(LGBTQIA.objects.order_by('name').values_list('name', flat=True))
        data['other_identity_options'] = list(OtherIdentity.objects.order_by('name').values_list('name', flat=True))
    except Exception:
        pass
    return JsonResponse(data, safe=False)

# --- Deferred Subscription Activation Helper ---
def _attempt_subscription_activation(user):
    """If user has passed payment step (customer + payment method stored) and
    profile & license appear valid, create the actual Stripe subscription and
    mark onboarding_status active.

    Silent no-op if prerequisites not met.
    """
    from django.conf import settings as _settings
    from users.models_profile import TherapistProfile
    from .models import Subscription
    import stripe as _stripe
    if getattr(user, 'onboarding_status', '') != 'pending_profile_completion':
        return
    profile = TherapistProfile.objects.filter(user=user).first()
    if not profile:
        return
    # Basic validation: require license_type, license_number, license_state (2 chars), at least first & last name
    if not (profile.license_type and profile.license_number and profile.license_state and len(profile.license_state) == 2):
        return
    if not (profile.first_name and profile.last_name):
        return
    # Ensure there is a subscription record with stored customer + payment method but no stripe_subscription_id yet
    sub = Subscription.objects.filter(user=user).exclude(stripe_customer_id__isnull=True).exclude(stripe_payment_method_id__isnull=True).filter(stripe_subscription_id__isnull=True).last()
    if not sub or not sub.subscription_type:
        return
    # Create subscription in Stripe
    price_id = sub.subscription_type.stripe_plan_id_monthly if sub.interval == 'monthly' else sub.subscription_type.stripe_plan_id_annual
    if not price_id:
        return
    _stripe.api_key = _settings.STRIPE_SECRET_KEY
    try:
        stripe_sub = _stripe.Subscription.create(
            customer=sub.stripe_customer_id,
            items=[{'price': price_id}],
            default_payment_method=sub.stripe_payment_method_id,
            expand=["latest_invoice.payment_intent"],
        )
        sub.stripe_subscription_id = stripe_sub.id
        sub.save(update_fields=['stripe_subscription_id'])
        # Activate user
        user.onboarding_status = 'active'
        user.save(update_fields=['onboarding_status'])
    except Exception:
        # Leave user pending; they'll stay in pending_profile_completion until next successful attempt
        return


from django.db.models import Q

@login_required
def members_home(request):
    return render(request, 'users/members/home.html')


@login_required
def members_profile(request):
    # Reuse unified editor
    return redirect('edit_profile')


@login_required
def members_account(request):
    from .models import Subscription
    sub = Subscription.objects.filter(user=request.user).order_by('-created_at').first()
    return render(request, 'users/members/account.html', {
        'subscription': sub,
    })


@login_required
def members_feed(request):
    # Optional sort selection (recent|top)
    sort = (request.GET.get('sort') or '').strip().lower()
    if sort not in {'recent', 'top'}:
        sort = 'recent'
    # Optional search query
    query = (request.GET.get('q') or '').strip()
    # Create new post (simple form fallback)
    if request.method == 'POST' and request.POST.get('action') == 'create':
        content = (request.POST.get('content') or '').strip()
        # Visibility: default to members for feed posts (UI doesn't expose a selector here)
        visibility = (request.POST.get('visibility') or 'members').strip()
        post_type = (request.POST.get('post_type') or 'text').strip()
        title = (request.POST.get('title') or '').strip() or None
        scheduled_at = (request.POST.get('scheduled_at') or '').strip() or None
        event_start_at = (request.POST.get('event_start_at') or '').strip() or None
        event_location = (request.POST.get('event_location') or '').strip() or None
        event_url = (request.POST.get('event_url') or '').strip() or None
        celebrate_type = (request.POST.get('celebrate_type') or '').strip() or None
        if content or title or (request.FILES.getlist('media') or []):
            from .models import FeedPost, FeedMedia
            if visibility not in dict(FeedPost.VISIBILITY_CHOICES):
                visibility = 'members'
            if post_type not in dict(FeedPost.POST_TYPE_CHOICES):
                post_type = 'text'
            post = FeedPost.objects.create(
                author=request.user,
                content=content[:5000],
                visibility=visibility,
                post_type=post_type,
                title=title,
            )
            # schedule if present
            from django.utils.dateparse import parse_datetime
            if scheduled_at:
                dt = parse_datetime(scheduled_at)
                if dt:
                    post.scheduled_at = dt
                    post.is_published = False
            if post_type == 'event':
                if event_start_at:
                    dt2 = parse_datetime(event_start_at)
                    if dt2:
                        post.event_start_at = dt2
                post.event_location = event_location
                post.event_url = event_url
            if post_type == 'celebrate':
                post.celebrate_type = celebrate_type
            post.save()
            # Handle media uploads from composer form (images/videos)
            files = request.FILES.getlist('media') or []
            if files:
                # Optional per-file metadata (e.g., stock image attribution) sent as JSON mapping of filename -> meta
                import json as _json
                try:
                    media_meta_map = _json.loads(request.POST.get('media_meta') or '{}')
                except Exception:
                    media_meta_map = {}
                any_image = False
                any_video = False
                # Limit number of files to avoid abuse
                # Single-media only for feed posts: take the first file
                for f in files[:1]:
                    ctype = (getattr(f, 'content_type', '') or '').lower()
                    name = getattr(f, 'name', '') or ''
                    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
                    # Fallback detection by extension if content_type is missing or generic
                    def guess_type():
                        if ctype.startswith('image/'):
                            return 'image'
                        if ctype.startswith('video/'):
                            return 'video'
                        if ext in {'jpg','jpeg','png','gif','webp','bmp'}:
                            return 'image'
                        if ext in {'mp4','mov','m4v','webm','avi','mkv'}:
                            return 'video'
                        return ''
                    mtype = guess_type()
                    try:
                        if mtype == 'image':
                            # 10MB cap for images
                            if getattr(f, 'size', 0) and f.size > 10 * 1024 * 1024:
                                continue
                            meta = None
                            fname = getattr(f, 'name', '')
                            if fname and isinstance(media_meta_map, dict):
                                meta = media_meta_map.get(fname)
                            FeedMedia.objects.create(post=post, file=f, type='image', meta=(meta or {}))
                            any_image = True
                        elif mtype == 'video':
                            # 60MB cap for videos
                            if getattr(f, 'size', 0) and f.size > 60 * 1024 * 1024:
                                continue
                            FeedMedia.objects.create(post=post, file=f, type='video', meta={})
                            any_video = True
                        else:
                            # Skip unsupported types silently
                            continue
                    except Exception:
                        # Skip problematic file but continue others
                        continue
                # Adjust post_type if it was left as text and media present
                if post.post_type == 'text' and (any_image or any_video):
                    post.post_type = 'video' if any_video else 'photo'
                    post.save(update_fields=['post_type'])
        # Post/Redirect/Get to avoid form resubmission
        return redirect('members_feed')
    # List visible posts
    from .models import FeedPost, Connection, FeedReaction
    # Accepted connections for current user (either direction)
    accepted_ids = set(Connection.objects.filter(
        Q(requester=request.user, status='accepted') | Q(addressee=request.user, status='accepted')
    ).values_list('requester_id', 'addressee_id'))
    # Flatten to user IDs excluding self duplicates
    connected_user_ids = set()
    for a, b in accepted_ids:
        if a:
            connected_user_ids.add(a)
        if b:
            connected_user_ids.add(b)
    connected_user_ids.discard(request.user.id)
    base_qs = FeedPost.objects.filter(
        Q(visibility__in=['public', 'members']) |
        Q(visibility='connections', author_id__in=list(connected_user_ids)) |
        Q(author=request.user)
    )
    # Apply search filter if present
    if query:
        search_q = (
            Q(content__icontains=query) |
            Q(title__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query) |
            Q(author__username__icontains=query) |
            Q(repost_of__content__icontains=query) |
            Q(repost_of__title__icontains=query)
        )
        base_qs = base_qs.filter(search_q)
    posts = base_qs.select_related('author', 'repost_of', 'repost_of__author')\
        .prefetch_related('comments__author', 'reactions', 'media', 'repost_of__media')\
        .order_by('-created_at')[:100]
    # Compute per-reaction counts for visible posts
    from django.db.models import Count
    post_list = list(posts)
    if post_list:
        counts = (
            FeedReaction.objects
            .filter(post__in=post_list)
            .values('post_id', 'reaction')
            .annotate(c=Count('id'))
        )
        # Initialize per post for ALL defined reaction choices dynamically (future-proof)
        all_reactions = list(dict(FeedReaction.REACTION_CHOICES).keys())
        rc_map = {}
        for p in post_list:
            rc_map[p.id] = {r: 0 for r in all_reactions}
            rc_map[p.id]['total'] = 0
        for row in counts:
            pid = row['post_id']
            r = row['reaction']
            c = row['c'] or 0
            if pid in rc_map and r in rc_map[pid]:
                rc_map[pid][r] = c
                rc_map[pid]['total'] += c
        # Attach for template access
        for p in post_list:
            # Provide a safe default including total
            default_counts = {r: 0 for r in (rc_map.get(p.id, {}) if rc_map.get(p.id, {}) else all_reactions)}
            if isinstance(default_counts, list):
                # If previous line produced list (when p.id missing), convert to dict
                default_counts = {r: 0 for r in all_reactions}
            default_counts['total'] = default_counts.get('total', 0)
            setattr(p, 'reaction_counts', rc_map.get(p.id, default_counts))
        # Reorder if sorting by top
        if sort == 'top':
            post_list.sort(key=lambda p: (getattr(p, 'reaction_counts', {}).get('total', 0), getattr(p, 'created_at', None)), reverse=True)
    # Current user's avatar (if any) for composer
    me_avatar_url = None
    try:
        from users.models_profile import TherapistProfile as _TP
        _prof = _TP.objects.filter(user=request.user).first()
        if _prof and getattr(_prof, 'profile_photo', None):
            try:
                me_avatar_url = _prof.profile_photo.url
            except Exception:
                me_avatar_url = None
    except Exception:
        me_avatar_url = None
    # Attach author avatars for posts (and original authors for reposts) to avoid extra queries in template
    try:
        from users.models_profile import TherapistProfile as _TP2
        author_ids = {p.author_id for p in post_list}
        for p in post_list:
            if getattr(p, 'repost_of', None):
                author_ids.add(p.repost_of.author_id)
        profiles = {pr.user_id: pr for pr in _TP2.objects.filter(user_id__in=author_ids)}
        for p in post_list:
            av = profiles.get(p.author_id)
            setattr(p, 'author_avatar_url', (getattr(av, 'profile_photo', None).url if av and getattr(av, 'profile_photo', None) else None))
            # Compose display name and license info for header
            try:
                u = p.author
                first = (getattr(av, 'first_name', '') or getattr(u, 'first_name', '') or '').strip()
                last = (getattr(av, 'last_name', '') or getattr(u, 'last_name', '') or '').strip()
                display_name = (f"{first} {last}".strip()) or (getattr(u, 'username', '') or getattr(u, 'email', ''))
                setattr(p, 'author_display_name', display_name)
                lt_name = getattr(getattr(av, 'license_type', None), 'name', None)
                lt_short = getattr(getattr(av, 'license_type', None), 'short_description', None)
                setattr(p, 'author_license_type', lt_name)
                setattr(p, 'author_license_type_short', lt_short)
            except Exception:
                setattr(p, 'author_display_name', getattr(p.author, 'get_full_name', lambda: '')() or p.author.username)
                setattr(p, 'author_license_type', None)
                setattr(p, 'author_license_type_short', None)
            if getattr(p, 'repost_of', None):
                pav = profiles.get(p.repost_of.author_id)
                setattr(p, 'orig_author_avatar_url', (getattr(pav, 'profile_photo', None).url if pav and getattr(pav, 'profile_photo', None) else None))
                try:
                    ou = p.repost_of.author
                    ofirst = (getattr(pav, 'first_name', '') or getattr(ou, 'first_name', '') or '').strip()
                    olast = (getattr(pav, 'last_name', '') or getattr(ou, 'last_name', '') or '').strip()
                    odisplay = (f"{ofirst} {olast}".strip()) or (getattr(ou, 'username', '') or getattr(ou, 'email', ''))
                    setattr(p, 'orig_author_display_name', odisplay)
                    olt_name = getattr(getattr(pav, 'license_type', None), 'name', None)
                    olt_short = getattr(getattr(pav, 'license_type', None), 'short_description', None)
                    setattr(p, 'orig_author_license_type', olt_name)
                    setattr(p, 'orig_author_license_type_short', olt_short)
                except Exception:
                    setattr(p, 'orig_author_display_name', getattr(p.repost_of.author, 'get_full_name', lambda: '')() or p.repost_of.author.username)
                    setattr(p, 'orig_author_license_type', None)
                    setattr(p, 'orig_author_license_type_short', None)
    except Exception:
        pass
    return render(request, 'users/members/feed.html', {
        'posts': post_list,
        'current_sort': sort,
        'me_avatar_url': me_avatar_url,
    'query': query,
        'me_id': request.user.id,
    })


@login_required
@require_http_methods(["GET"])
def api_feed_stock_images(request):
    """Search royalty-free stock images for post composer. Returns a normalized list of results.

    Query params:
      - q: search term (required)
      - page: page number (default 1)
      - per_page: items per page (default 20, max 30)

    Backends supported via settings API keys (prefer Pexels if both present):
      - PEXELS_API_KEY: https://www.pexels.com/api/
      - UNSPLASH_ACCESS_KEY: https://unsplash.com/documentation

    For safety, only return URLs intended for hotlinking (provider-sanctioned) and attribution fields.
    """
    import math
    from django.conf import settings
    import requests
    q = (request.GET.get('q') or '').strip()
    try:
        page = max(1, int(request.GET.get('page') or 1))
    except Exception:
        page = 1
    try:
        per_page = int(request.GET.get('per_page') or 20)
    except Exception:
        per_page = 20
    per_page = max(1, min(per_page, 30))
    if not q:
        return JsonResponse({'results': [], 'total': 0, 'page': page, 'per_page': per_page})

    PEXELS_KEY = getattr(settings, 'PEXELS_API_KEY', None)
    UNSPLASH_KEY = getattr(settings, 'UNSPLASH_ACCESS_KEY', None)
    results = []
    total = 0
    try:
        if PEXELS_KEY:
            url = 'https://api.pexels.com/v1/search'
            headers = {'Authorization': PEXELS_KEY}
            params = {'query': q, 'per_page': per_page, 'page': page}
            resp = requests.get(url, headers=headers, params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get('photos', []):
                    src = p.get('src', {})
                    # Use large variant for composer preview; original available if needed
                    results.append({
                        'id': f"pexels_{p.get('id')}",
                        'thumb_url': src.get('medium') or src.get('small') or src.get('tiny'),
                        'full_url': src.get('large2x') or src.get('large') or src.get('original'),
                        'width': p.get('width'),
                        'height': p.get('height'),
                        'provider': 'pexels',
                        'attribution': (p.get('photographer') or '').strip(),
                        'attribution_url': p.get('photographer_url'),
                        'license': 'Pexels License',
                        'license_url': 'https://www.pexels.com/license/',
                    })
                total = data.get('total_results', 0)
            else:
                # Propagate provider errors (e.g., 401 invalid key) with a generic error code
                code = 'unauthorized' if resp.status_code in (401, 403) else 'provider_http'
                return JsonResponse({'results': [], 'total': 0, 'page': page, 'per_page': per_page, 'error': code}, status=502)
        elif UNSPLASH_KEY:
            url = 'https://api.unsplash.com/search/photos'
            headers = {'Authorization': f'Client-ID {UNSPLASH_KEY}'}
            params = {'query': q, 'per_page': per_page, 'page': page, 'content_filter': 'high', 'orientation': 'landscape'}
            resp = requests.get(url, headers=headers, params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get('results', []):
                    urls = p.get('urls', {})
                    user = p.get('user', {})
                    results.append({
                        'id': f"unsplash_{p.get('id')}",
                        'thumb_url': urls.get('small') or urls.get('thumb'),
                        'full_url': urls.get('regular') or urls.get('full'),
                        'width': p.get('width'),
                        'height': p.get('height'),
                        'provider': 'unsplash',
                        'attribution': (user.get('name') or user.get('username') or '').strip(),
                        'attribution_url': user.get('links', {}).get('html') or user.get('portfolio_url'),
                        'license': 'Unsplash License',
                        'license_url': 'https://unsplash.com/license',
                    })
                total = data.get('total', 0)
            else:
                code = 'unauthorized' if resp.status_code in (401, 403) else 'provider_http'
                return JsonResponse({'results': [], 'total': 0, 'page': page, 'per_page': per_page, 'error': code}, status=502)
        else:
            # No API keys; in DEBUG provide placeholder results so UI can be exercised
            if getattr(settings, 'DEBUG', False):
                import hashlib
                count = per_page
                base_id = (page - 1) * per_page
                # Derive a deterministic seed from the search query so different queries yield different images
                q_bytes = (q or 'default').encode('utf-8')
                q_hash = int(hashlib.md5(q_bytes).hexdigest(), 16) % 10_000_000
                results = []
                for i in range(count):
                    seed = (q_hash + base_id + i + 1)
                    thumb = f'https://picsum.photos/seed/{seed}/300/200'
                    full = f'https://picsum.photos/seed/{seed}/1200/800'
                    results.append({
                        'id': f'picsum_{seed}',
                        'thumb_url': thumb,
                        'full_url': full,
                        'width': 1200,
                        'height': 800,
                        'provider': 'picsum.dev',
                        'attribution': 'Lorem Picsum (demo)',
                        'attribution_url': 'https://picsum.photos/',
                        'license': 'Placeholder (dev only)',
                        'license_url': 'https://picsum.photos/',
                    })
                return JsonResponse({'results': results, 'total': 9999, 'page': page, 'per_page': per_page, 'note': 'DEBUG placeholder images'})
            # Otherwise return explicit setup note
            return JsonResponse({'results': [], 'total': 0, 'page': page, 'per_page': per_page, 'note': 'No stock image provider configured'})
    except Exception as ex:
        return JsonResponse({'results': [], 'total': 0, 'page': page, 'per_page': per_page, 'error': 'provider_error'}, status=502)

    return JsonResponse({'results': results, 'total': total, 'page': page, 'per_page': per_page})


@login_required
@require_http_methods(["POST"])
def api_feed_repost(request, post_id):
    """Create a repost pointing to an existing post. Allows optional note content."""
    from .models import FeedPost
    orig = FeedPost.objects.filter(id=post_id).select_related('author').first()
    if not orig:
        return JsonResponse({'error': 'Not found'}, status=404)
    # Optional content note
    note = (request.POST.get('content') or '').strip()
    try:
        new_post = FeedPost.objects.create(
            author=request.user,
            content=note[:2000],
            visibility='members',
            post_type='text',
            title=None,
            repost_of=orig,
        )
    except Exception as ex:
        return JsonResponse({'error': 'Create failed', 'detail': str(ex)}, status=500)
    return JsonResponse({'ok': True, 'id': new_post.id})


@login_required
@require_http_methods(["POST"])
def api_feed_react(request, post_id):
    from .models import FeedPost, FeedReaction
    reaction = (request.POST.get('reaction') or 'like').strip()
    if reaction not in dict(FeedReaction.REACTION_CHOICES):
        reaction = 'like'
    post = FeedPost.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    # Toggle or set
    obj, created = FeedReaction.objects.update_or_create(post=post, user=request.user, defaults={'reaction': reaction})
    return JsonResponse({'ok': True, 'reaction': obj.reaction, 'created': created})


@login_required
@require_http_methods(["POST"]) 
def api_feed_comment(request, post_id):
    from .models import FeedPost, FeedComment
    post = FeedPost.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    content = (request.POST.get('content') or '').strip()
    parent_id = request.POST.get('parent_id')
    if not content:
        return JsonResponse({'error': 'Empty'}, status=400)
    parent = None
    if parent_id:
        parent = FeedComment.objects.filter(id=parent_id, post=post).first()
    c = FeedComment.objects.create(post=post, author=request.user, content=content[:2000], parent=parent)
    return JsonResponse({'ok': True, 'id': c.id, 'content': c.content, 'author': request.user.get_full_name() or request.user.username, 'created_at': c.created_at.isoformat()})


@login_required
@require_http_methods(["POST"]) 
def api_feed_media_upload(request, post_id):
    from .models import FeedPost, FeedMedia
    post = FeedPost.objects.filter(id=post_id, author=request.user).first()
    if not post:
        return JsonResponse({'error': 'Not found or no permission'}, status=404)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file'}, status=400)
    # naive type detection
    mtype = 'image' if (f.content_type or '').startswith('image/') else 'video'
    media = FeedMedia.objects.create(post=post, file=f, type=mtype)
    return JsonResponse({'ok': True, 'id': media.id, 'type': media.type, 'url': media.file.url})


@login_required
@require_http_methods(["DELETE", "POST"])
def api_feed_post_item(request, post_id):
    """Delete the current user's post (supports DELETE or POST with action=delete)."""
    from .models import FeedPost
    post = FeedPost.objects.filter(id=post_id, author=request.user).first()
    if not post:
        # Hide existence when not owner
        return JsonResponse({'error': 'Not found'}, status=404)
    # Allow HTML forms to POST with action=delete
    if request.method == 'POST' and (request.POST.get('action') or '').lower() != 'delete':
        return JsonResponse({'error': 'Unsupported'}, status=400)
    try:
        post.delete()
    except Exception as ex:
        return JsonResponse({'error': 'Delete failed', 'detail': str(ex)}, status=500)
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["GET"])
def api_feed_reactions(request, post_id):
    """Return list of reactions for a post with user display, avatar, and license info."""
    from .models import FeedPost, FeedReaction
    post = FeedPost.objects.filter(id=post_id).first()
    if not post:
        return JsonResponse({'error': 'Not found'}, status=404)
    qs = FeedReaction.objects.filter(post=post).select_related('user').order_by('-created_at')
    user_ids = [r.user_id for r in qs]
    profiles = {}
    try:
        from users.models_profile import TherapistProfile as _TP
        profiles = {p.user_id: p for p in _TP.objects.filter(user_id__in=user_ids).select_related('license_type')}
    except Exception:
        profiles = {}
    def display_name(u, p):
        first = (getattr(p, 'first_name', '') or getattr(u, 'first_name', '') or '').strip()
        last = (getattr(p, 'last_name', '') or getattr(u, 'last_name', '') or '').strip()
        return (f"{first} {last}".strip()) or (getattr(u, 'username', '') or getattr(u, 'email', ''))
    items = []
    for r in qs:
        u = r.user
        p = profiles.get(r.user_id)
        try:
            avatar = (getattr(getattr(p, 'profile_photo', None), 'url', None) if p else None)
        except Exception:
            avatar = None
        lt = getattr(getattr(p, 'license_type', None), 'name', None) if p else None
        lt_short = getattr(getattr(p, 'license_type', None), 'short_description', None) if p else None
        items.append({
            'user_id': r.user_id,
            'display_name': display_name(u, p),
            'avatar_url': avatar,
            'license_type': lt,
            'license_type_short': lt_short,
            'reaction': r.reaction,
            'created_at': r.created_at.isoformat(),
        })
    # Optional: counts by reaction
    from django.db.models import Count
    counts_qs = (
        FeedReaction.objects.filter(post=post)
        .values('reaction')
        .annotate(c=Count('id'))
    )
    counts = {row['reaction']: row['c'] for row in counts_qs}
    return JsonResponse({'ok': True, 'reactions': items, 'counts': counts})


@login_required
@require_http_methods(["GET"])
def api_feed_new_count(request):
    """Return count of new visible posts with id greater than since_id."""
    from django.db.models import Q
    from .models import FeedPost, Connection
    try:
        since_id = int(request.GET.get('since_id') or 0)
    except (ValueError, TypeError):
        since_id = 0
    # Build connections set (same logic as members_feed)
    accepted_ids = set(Connection.objects.filter(
        Q(requester=request.user, status='accepted') | Q(addressee=request.user, status='accepted')
    ).values_list('requester_id', 'addressee_id'))
    connected_user_ids = set()
    for a, b in accepted_ids:
        if a: connected_user_ids.add(a)
        if b: connected_user_ids.add(b)
    connected_user_ids.discard(request.user.id)
    qs = FeedPost.objects.filter(
        Q(id__gt=since_id),
        Q(visibility__in=['public', 'members']) |
        Q(visibility='connections', author_id__in=list(connected_user_ids)) |
        Q(author=request.user)
    )
    return JsonResponse({'ok': True, 'new_count': qs.count()})


@login_required
@ensure_csrf_cookie
def members_connections(request):
    from django.db.models import Q
    from .models import Connection
    # Lists: pending received, pending sent, and accepted
    received = Connection.objects.filter(addressee=request.user, status='pending').order_by('-created_at')
    sent = Connection.objects.filter(requester=request.user, status='pending').order_by('-created_at')
    accepted = Connection.objects.filter(
        status='accepted'
    ).filter(
        Q(requester=request.user) | Q(addressee=request.user)
    ).order_by('-updated_at', '-created_at')
    return render(request, 'users/members/connections.html', {
        'received': received,
    'received_count': received.count(),
        'sent': sent,
        'accepted': accepted,
    })


@login_required
@ensure_csrf_cookie
def members_invitations(request):
    """Page listing all current pending invitations received by the user."""
    from .models import Connection
    received = Connection.objects.filter(addressee=request.user, status='pending').order_by('-created_at')
    return render(request, 'users/members/invitations.html', {
        'received': received,
    'received_count': received.count(),
    })


@login_required
def members_my_connections(request):
    """List all accepted connections for the current user."""
    from django.db.models import Q
    from .models import Connection
    connections = (Connection.objects
                   .filter(status='accepted')
                   .filter(Q(requester=request.user) | Q(addressee=request.user))
                   .select_related('requester', 'addressee')
                   .order_by('-updated_at', '-created_at'))
    # Pending invitations received count (for sidebar badge)
    received_count = Connection.objects.filter(addressee=request.user, status='pending').count()
    return render(request, 'users/members/my_connections.html', {
        'connections': connections,
        'received_count': received_count,
    })


@login_required
@require_http_methods(["POST"])
def api_connection_accept(request, conn_id: int):
    """Accept a pending connection where current user is the addressee."""
    from .models import Connection
    try:
        c = Connection.objects.select_related('requester', 'addressee').get(id=conn_id)
    except Connection.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    if c.addressee_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    if c.status != 'pending':
        return JsonResponse({'ok': False, 'error': 'not_pending'}, status=400)
    c.status = 'accepted'
    c.save(update_fields=['status', 'updated_at'])
    # Peer is the requester when accepting
    peer = c.requester
    return JsonResponse({'ok': True, 'connection': {
        'id': c.id,
        'status': c.status,
        'peer_id': peer.id,
        'peer_name': f"{peer.first_name} {peer.last_name}".strip() or peer.email,
        'peer_email': peer.email,
    }})


@login_required
@require_http_methods(["POST", "DELETE"])
def api_connection_delete(request, conn_id: int):
    """Delete a connection or pending request.
    - If pending and addressee is current user: acts like decline.
    - If pending and requester is current user: cancel sent request.
    - If accepted and either side is current user: remove connection.
    """
    from .models import Connection
    try:
        c = Connection.objects.get(id=conn_id)
    except Connection.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
    if c.requester_id != request.user.id and c.addressee_id != request.user.id:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    c.delete()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["POST"])
def api_connection_request(request, user_id: int):
    """Send a connection request to another user.
    Behavior:
    - No-op if already connected or pending request exists from current user.
    - If a pending request exists from the other user to current user, auto-accept it.
    - Cannot connect to self.
    Returns JSON with connection id and status (pending or accepted).
    """
    from django.db.models import Q
    from .models import Connection
    # Prevent self-connect
    if user_id == request.user.id:
        return JsonResponse({'ok': False, 'error': 'cannot_connect_to_self'}, status=400)
    # Resolve peer
    peer = User.objects.filter(id=user_id).first()
    if not peer:
        return JsonResponse({'ok': False, 'error': 'user_not_found'}, status=404)
    # Existing same-direction request?
    existing = Connection.objects.filter(requester=request.user, addressee=peer).first()
    if existing:
        # If already accepted or pending, just return it
        return JsonResponse({'ok': True, 'connection': {
            'id': existing.id,
            'status': existing.status,
            'peer_id': peer.id,
            'peer_name': (f"{peer.first_name} {peer.last_name}".strip() or peer.email),
            'peer_email': peer.email,
        }})
    # Reverse existing?
    reverse = Connection.objects.filter(requester=peer, addressee=request.user).first()
    if reverse:
        if reverse.status == 'pending':
            reverse.status = 'accepted'
            reverse.save(update_fields=['status', 'updated_at'])
        # accepted (or now accepted) -> return that
        return JsonResponse({'ok': True, 'connection': {
            'id': reverse.id,
            'status': reverse.status,
            'peer_id': peer.id,
            'peer_name': (f"{peer.first_name} {peer.last_name}".strip() or peer.email),
            'peer_email': peer.email,
        }})
    # Create new pending request
    c = Connection.objects.create(requester=request.user, addressee=peer, status='pending')
    return JsonResponse({'ok': True, 'connection': {
        'id': c.id,
        'status': c.status,
        'peer_id': peer.id,
        'peer_name': (f"{peer.first_name} {peer.last_name}".strip() or peer.email),
        'peer_email': peer.email,
    }}, status=201)


@login_required
@require_http_methods(["GET"]) 
def api_connections_discover(request):
    """Members-only discover endpoint to find other therapists to connect with.
    Filters: q (name/email/text), school, practice, city, state, within (miles), sort (distance|name).
    Behavior: excludes current user and existing accepted connections. Supports suggestions by shared schools.
    Returns JSON list of up to 50 candidates with {id,name,license,city,state,distance}.
    """
    from django.db.models import Q
    from .models import Connection
    from users.models_profile import TherapistProfile, ZipCode
    # Base queryset: active users (include those still completing onboarding to increase pool)
    qs = (TherapistProfile.objects
          .filter(user__is_active=True)
          .select_related('license_type','user')
          .prefetch_related('locations','educations'))
    # Exclude self
    qs = qs.exclude(user=request.user)
    # Exclude already connected (accepted) with current user; allow pending to appear as suggestions
    connected_pairs = Connection.objects.filter(
        (Q(requester=request.user) | Q(addressee=request.user)) & Q(status='accepted')
    ).values_list('requester_id','addressee_id')
    exclude_ids = set()
    for a,b in connected_pairs:
        if a: exclude_ids.add(a)
        if b: exclude_ids.add(b)
    exclude_ids.discard(request.user.id)
    if exclude_ids:
        qs = qs.exclude(user_id__in=list(exclude_ids))

    # Filters
    q = (request.GET.get('q') or '').strip()
    school = (request.GET.get('school') or '').strip()
    practice = (request.GET.get('practice') or '').strip()
    city = (request.GET.get('city') or '').strip()
    state = (request.GET.get('state') or '').strip()
    suggest = (request.GET.get('suggest') or '').lower() in {'1','true','yes'}
    within = request.GET.get('within')
    try:
        within_miles = int(within) if within else 150
    except (TypeError, ValueError):
        within_miles = 150
    sort = (request.GET.get('sort') or 'distance').strip()

    if q:
        name_q = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(user__email__icontains=q)
        text_q = Q(intro_statement__icontains=q) | Q(personal_statement_q1__icontains=q) | Q(personal_statement_q2__icontains=q) | Q(personal_statement_q3__icontains=q)
        loc_q = Q(locations__city__icontains=q) | Q(locations__state__icontains=q)
        qs = qs.filter(name_q | text_q | loc_q)
    if school:
        qs = qs.filter(educations__school__icontains=school)
    if practice:
        qs = qs.filter(practice_name__icontains=practice)
    if city:
        qs = qs.filter(locations__city__icontains=city)
    if state:
        from users.utils.state_normalize import normalize_state
        st = normalize_state(state)
        qs = qs.filter(Q(locations__state__iexact=st) | Q(locations__state__icontains=state))

    # Suggestions by shared schools if requested and no explicit filters
    if suggest and not (q or school or practice or city or state):
        try:
            my_schools = list({e.school.strip() for e in request.user.therapistprofile.educations.all() if (e.school or '').strip()})
        except Exception:
            my_schools = []
        if my_schools:
            sub = TherapistProfile.objects.filter(educations__school__in=my_schools)
            qs = qs.filter(id__in=sub.values('id'))

    qs = qs.distinct()

    # Compute distances if user_zip known
    user_zip = request.session.get('user_zip')
    zip_row = None
    if user_zip:
        try:
            import re
            uz = re.match(r"\d{5}", user_zip or "")
            uz = uz.group(0) if uz else user_zip
            zip_row = ZipCode.objects.filter(pk=uz).first()
        except Exception:
            zip_row = None
    results = []
    def haversine(lat1, lon1, lat2, lon2):
        import math
        R = 3958.8
        phi1 = math.radians(lat1); phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    # Prepare location zip rows
    zip_rows = {}
    if zip_row:
        try:
            loc_zips = set(qs.values_list('locations__zip', flat=True))
            from users.models_profile import ZipCode as Z
            zip_rows = {z.zip: z for z in Z.objects.filter(zip__in=loc_zips)}
        except Exception:
            zip_rows = {}
    # Iterate limited set first for performance
    candidates = list(qs[:200])
    for prof in candidates:
        dist = None
        city_val = None
        state_val = None
        practice_val = None
        # Determine primary practice from primary location if available, else profile.practice_name
        try:
            locs = list(prof.locations.all())
        except Exception:
            locs = []
        if locs:
            # choose first for city/state display; distance computed across all
            city_val = getattr(locs[0], 'city', None)
            state_val = getattr(locs[0], 'state', None)
            try:
                primary_loc = next((l for l in locs if getattr(l,'is_primary_address', False)), None)
            except Exception:
                primary_loc = None
            if primary_loc and getattr(primary_loc, 'practice_name', None):
                practice_val = primary_loc.practice_name
        if zip_row and locs:
            mind = None
            for loc in locs:
                zr = zip_rows.get(getattr(loc, 'zip', None))
                if zr and zr.latitude and zr.longitude and zip_row.latitude and zip_row.longitude:
                    try:
                        d = haversine(float(zip_row.latitude), float(zip_row.longitude), float(zr.latitude), float(zr.longitude))
                    except Exception:
                        continue
                    if mind is None or d < mind:
                        mind = d
                        city_val = getattr(loc, 'city', city_val)
                        state_val = getattr(loc, 'state', state_val)
            dist = round(mind, 1) if mind is not None else None
        # Fallback practice name from profile
        if not practice_val:
            practice_val = getattr(prof, 'practice_name', None)
        # Profile photo url (safe)
        try:
            photo_url = prof.profile_photo.url if getattr(prof, 'profile_photo', None) else None
        except Exception:
            photo_url = None
        # Education: prefer latest graduation year if present
        school_name = None
        school_year = None
        try:
            edus = list(prof.educations.all())
        except Exception:
            edus = []
        if edus:
            # pick with greatest numeric year_graduated
            def yr(e):
                y = (getattr(e, 'year_graduated', '') or '').strip()
                return int(y) if (y.isdigit() and len(y)==4) else None
            by_year = sorted([e for e in edus if yr(e) is not None], key=lambda e: yr(e), reverse=True)
            chosen = by_year[0] if by_year else edus[0]
            school_name = getattr(chosen, 'school', None)
            yv = (getattr(chosen, 'year_graduated', '') or '').strip()
            school_year = yv if (yv.isdigit() and len(yv)==4) else None
        results.append({
            'id': prof.user_id,
            'first_name': prof.first_name,
            'last_name': prof.last_name,
            'name': f"{prof.first_name} {prof.last_name}".strip(),
            'license_type': getattr(getattr(prof,'license_type',None),'name', None),
            'license_type_short': getattr(getattr(prof,'license_type',None),'short_description', None),
            'city': city_val,
            'state': state_val,
            'distance': dist,
            'photo_url': photo_url,
            'practice_name': practice_val,
            'school': school_name,
            'school_year': school_year,
            'slug': getattr(prof, 'slug', None),
        })
    # Filter by within miles if distance available
    if zip_row and within_miles is not None:
        results = [r for r in results if (r['distance'] is None or r['distance'] <= within_miles)]
    # Sort
    if sort == 'name':
        results.sort(key=lambda r: (r['last_name'] or '', r['first_name'] or ''))
    else:
        results.sort(key=lambda r: (r['distance'] if r['distance'] is not None else float('inf')))
    return JsonResponse({'ok': True, 'results': results[:50]})


@login_required
def members_blog(request):
    from .models_blog import BlogPost, BlogTag
    # Me avatar for composer (similar to feed)
    me_avatar_url = None
    try:
        _prof = TherapistProfile.objects.filter(user=request.user).only('profile_photo').first()
        if _prof and _prof.profile_photo:
            me_avatar_url = _prof.profile_photo.url
    except Exception:
        me_avatar_url = None
    # Filters
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'recent').strip().lower()
    posts = (
        BlogPost.objects
        .filter(published=True, visibility__in=['members','both','public'])
        .select_related('author')
        .prefetch_related('tags', 'media')
    )
    if q:
        from django.db.models import Q
        posts = posts.filter(
            Q(title__icontains=q) |
            Q(content__icontains=q) |
            Q(tags__name__icontains=q) |
            Q(author__first_name__icontains=q) |
            Q(author__last_name__icontains=q)
        ).distinct()
    if sort == 'oldest':
        posts = posts.order_by('created_at')
    else:
        sort = 'recent'
        posts = posts.order_by('-created_at')
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Sidebar data
    recent_posts = BlogPost.objects.filter(published=True, visibility__in=['members','both','public']).order_by('-created_at')[:6]
    tags = BlogTag.objects.all().order_by('name')
    return render(request, 'users/members/blog.html', {
        'page_obj': page_obj,
        'q': q,
        'current_sort': sort,
        'me_avatar_url': me_avatar_url,
        'recent_posts': recent_posts,
        'tags': tags,
    })


@login_required
def members_stats(request):
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
    return render(request, 'users/members/stats.html', {
        'stats': stats,
    })

