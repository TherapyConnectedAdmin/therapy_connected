# About page view
def about_page(request):
    return render(request, 'about.html')
from django.shortcuts import render, redirect
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from users.models import SubscriptionType, TherapistProfileStats
from users.models_profile import TherapistProfile
from users.models_blog import BlogPost

# Features page view
def features_page(request):
    return render(request, 'features.html')

# Pricing page view
def pricing_page(request):
    plans = SubscriptionType.objects.filter(active=True).order_by('price_monthly')
    return render(request, 'pricing.html', {'plans': plans})
def therapists_page(request):
    query = request.GET.get('q', '').strip()
    tier = request.GET.get('tier', '').strip()
    specialty = request.GET.get('specialty', '').strip()
    therapists = TherapistProfile.objects.filter(user__is_active=True, user__onboarding_status='active').prefetch_related('locations')
    if query:
        from users.utils.state_normalize import normalize_state
        normalized_query = normalize_state(query)
        q_obj = (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(credentials__license_type__name__icontains=query) |
            Q(credentials__license_type__description__icontains=query) |
            Q(locations__city__icontains=query) |
            Q(locations__state__icontains=query) |
            Q(locations__state__iexact=normalized_query) |
            Q(personal_statement_q1__icontains=query) |
            Q(personal_statement_q2__icontains=query) |
            Q(personal_statement_q3__icontains=query)
        )
        therapists = therapists.filter(q_obj)
    if tier:
        therapists = therapists.filter(license_type__name__iexact=tier)
    # Removed specialty filtering due to missing PracticeAreaTag model

    user_zip = request.session.get('user_zip')
    # Distance-based default ordering and filtering
    if user_zip:
        try:
            import math, re
            from users.models_profile import ZipCode
            user_zip_clean = re.match(r"\d{5}", user_zip or "")
            user_zip_clean = user_zip_clean.group(0) if user_zip_clean else user_zip
            user_zip_row = ZipCode.objects.filter(pk=user_zip_clean).first()
            if not user_zip_row:
                raise ValueError('User ZIP not found in ZipCode table')
            # Preload all distinct location zips appearing in queryset
            location_zips = set(therapists.values_list('locations__zip', flat=True))
            zip_rows = {z.zip: z for z in ZipCode.objects.filter(zip__in=location_zips)}

            def haversine(lat1, lon1, lat2, lon2):
                R = 3958.8
                phi1 = math.radians(lat1)
                phi2 = math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return R * c

            def compute_min_distance(therapist):
                min_d = None
                nearest_loc = None
                for loc in therapist.locations.all():
                    zr = zip_rows.get(getattr(loc, 'zip', None))
                    if zr:
                        d = haversine(float(user_zip_row.latitude), float(user_zip_row.longitude), float(zr.latitude), float(zr.longitude))
                        if min_d is None or d < min_d:
                            min_d = d
                            nearest_loc = loc
                if nearest_loc is not None:
                    # Attach for template usage (city/state display of closest location)
                    therapist.closest_location = nearest_loc
                return round(min_d, 1) if min_d is not None else None

            therapists = list(therapists.distinct())
            for t in therapists:
                t.distance = compute_min_distance(t)
            therapists.sort(key=lambda t: t.distance if t.distance is not None else float('inf'))
            RADIUS = 150
            within_radius = [t for t in therapists if t.distance is not None and t.distance <= RADIUS]
            if len(within_radius) >= 150:
                therapists = within_radius
            else:
                therapists = (within_radius + [t for t in therapists if t not in within_radius])[:150]
        except Exception:
            therapists = list(therapists.distinct().order_by('-user__last_login')[:150])
            for t in therapists:
                t.distance = None
    else:
        # No user zip: just take most recently active up to 150
        therapists = list(therapists.distinct().order_by('-user__last_login')[:150])
        for t in therapists:
            t.distance = None

    # Absolute fallback: if still empty, relax filters (include non-active onboarding) then still ensure distance attr
    if not therapists:
        fallback_qs = TherapistProfile.objects.filter(user__is_active=True).prefetch_related('locations').order_by('-user__last_login')[:150]
        therapists = list(fallback_qs)
        for t in therapists:
            if not hasattr(t, 'distance'):
                t.distance = None

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get('page', 1)
    paginator = Paginator(therapists, 10)
    try:
        therapists_page_obj = paginator.page(page)
    except PageNotAnInteger:
        therapists_page_obj = paginator.page(1)
    except EmptyPage:
        therapists_page_obj = paginator.page(paginator.num_pages)

    # Ensure .distance is always set for template consistency
    for therapist in therapists_page_obj.object_list:
        if not hasattr(therapist, 'distance') or therapist.distance is None:
            therapist.distance = None

    # After pagination, log search impressions and rank
    today = timezone.now().date()
    for idx, therapist in enumerate(therapists_page_obj.object_list, start=1):
        stats, _ = TherapistProfileStats.objects.get_or_create(therapist=therapist.user, date=today)
        stats.search_impressions += 1
        stats.search_rank = idx  # last rank seen for today
        stats.save()

    # Zip meta for display
    user_zip_city = None
    user_zip_state = None
    if user_zip:
        try:
            from users.models_profile import ZipCode
            zrow = ZipCode.objects.filter(pk=user_zip[:5]).first()
            if zrow:
                user_zip_city = zrow.city
                user_zip_state = zrow.state
        except Exception:
            pass
    return render(request, 'therapists.html', {
        'therapists': therapists_page_obj,
        'paginator': paginator,
        'page_obj': therapists_page_obj,
        'user_zip': user_zip,
        'user_zip_city': user_zip_city,
        'user_zip_state': user_zip_state,
        'user_zip_is_default': False,
    })

def set_zip(request):
    zip_code = request.GET.get('zip')
    if zip_code:
        # Ensure we have the ZIP stored (dynamic enrichment if missing)
        try:
            from users.location_utils import ensure_zipcode
            ensure_zipcode(zip_code)
        except Exception:
            pass
        request.session['user_zip'] = zip_code[:5]
        return JsonResponse({'status': 'ok', 'zip': zip_code[:5]})
    return JsonResponse({'status': 'error', 'message': 'No zip provided'}, status=400)

def geo_zip(request):
    """Return nearest stored ZIP for provided lat/lon using local ZipCode table.
    If table is empty returns 404. (Future: add bounding-box prefilter or spatial index.)
    """
    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid coordinates'}, status=400)
    try:
        from users.location_utils import nearest_zip_from_coordinates, ensure_zipcode
        zc = nearest_zip_from_coordinates(lat, lng)
        if not zc:
            return JsonResponse({'status': 'error', 'message': 'No stored ZIPs'}, status=404)
        # Defensive: ensure_zipcode (no-op if exists)
        ensure_zipcode(zc)
        return JsonResponse({'status': 'ok', 'zip': zc})
    except Exception as e:
        payload = {'status': 'error', 'message': 'Lookup failed'}
        if getattr(settings, 'DEBUG', False):
            payload['exception'] = f"{e.__class__.__name__}: {e}"
        return JsonResponse(payload, status=500)


def home(request):
    """Home page view that now attaches closest_location similar to therapists_page.
    Shows top therapists (max 6) ordered by distance if user_zip known.
    """
    user_zip = request.session.get('user_zip')
    DEFAULT_ZIP = "10001"
    if not user_zip:
        user_zip = DEFAULT_ZIP
        user_zip_is_default = True
    else:
        user_zip_is_default = False

    query = request.GET.get('q', '').strip()
    therapists = (TherapistProfile.objects
                  .filter(user__is_active=True, user__onboarding_status='active')
                  .prefetch_related('locations'))
    if query:
        from users.utils.state_normalize import normalize_state
        normalized_query = normalize_state(query)
        q_obj = (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(personal_statement_q1__icontains=query) |
            Q(personal_statement_q2__icontains=query) |
            Q(personal_statement_q3__icontains=query) |
            Q(intro_statement__icontains=query) |
            Q(locations__city__icontains=query) |
            Q(locations__state__icontains=query) |
            Q(locations__state__iexact=normalized_query) |
            Q(credentials_note__icontains=query)
        )
        therapists = therapists.filter(q_obj)

    import math, re
    from users.models_profile import ZipCode
    # Clean user zip & fetch row
    user_zip_clean = re.match(r"\d{5}", user_zip or "")
    user_zip_clean = user_zip_clean.group(0) if user_zip_clean else user_zip
    user_zip_row = ZipCode.objects.filter(pk=user_zip_clean).first()

    def haversine(lat1, lon1, lat2, lon2):
        R = 3958.8
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    # Preload all location zip rows once
    therapist_zips = set(therapists.values_list('locations__zip', flat=True))
    zip_rows = {z.zip: z for z in ZipCode.objects.filter(zip__in=therapist_zips)}

    def compute_min_distance_and_attach(therapist):
        """Compute min distance for therapist; set therapist.closest_location; return rounded miles or None."""
        if not user_zip_row:
            return None
        min_d = None
        nearest_loc = None
        for loc in therapist.locations.all():
            zr = zip_rows.get(getattr(loc, 'zip', None))
            if zr:
                d = haversine(float(user_zip_row.latitude), float(user_zip_row.longitude), float(zr.latitude), float(zr.longitude))
                if min_d is None or d < min_d:
                    min_d = d
                    nearest_loc = loc
        if nearest_loc is not None:
            therapist.closest_location = nearest_loc
        return round(min_d, 1) if min_d is not None else None

    therapists = list(therapists.distinct())
    for t in therapists:
        t.distance = compute_min_distance_and_attach(t)

    # Order by distance (None last) and limit to 6
    therapists_final = sorted(therapists, key=lambda t: t.distance if t.distance is not None else float('inf'))[:6]

    from users.models_featured import FeaturedTherapistHistory, FeaturedBlogPostHistory
    today = timezone.now().date()
    # Try to get today's featured therapist and blog post from history
    featured_therapist_entry = FeaturedTherapistHistory.objects.filter(date=today).first()
    featured_blog_entry = FeaturedBlogPostHistory.objects.filter(date=today).first()
    top_therapist = featured_therapist_entry.therapist if featured_therapist_entry else (therapists_final[0] if therapists_final else None)
    # Ensure top_therapist has distance / closest_location if sourced from history outside therapists_final
    if top_therapist and not hasattr(top_therapist, 'distance'):
        try:
            top_therapist.distance = compute_min_distance_and_attach(top_therapist)
        except Exception:
            top_therapist.distance = None
    top_blog_post = featured_blog_entry.blog_post if featured_blog_entry else BlogPost.objects.filter(published=True).order_by('-created_at').first()
    # Add city/state meta for current zip
    user_zip_city = None
    user_zip_state = None
    if user_zip_row:
        user_zip_city = user_zip_row.city
        user_zip_state = user_zip_row.state
    return render(request, 'home.html', {
        'therapists': therapists_final,
        'top_blog_post': top_blog_post,
        'top_therapist': top_therapist,
        'user_zip': user_zip,
        'user_zip_city': user_zip_city,
        'user_zip_state': user_zip_state,
        'user_zip_is_default': user_zip_is_default,
    })

def subscribe(request):
    plans = SubscriptionType.objects.filter(active=True)
    return render(request, 'subscribe.html', {'plans': plans})

def select_plan(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan_interval = request.POST.get('plan_interval', 'monthly')
        if plan_id:
            request.session['selected_plan_id'] = plan_id
            request.session['selected_plan_interval'] = plan_interval
            return redirect('/users/register/')
    return redirect('/subscribe/')
