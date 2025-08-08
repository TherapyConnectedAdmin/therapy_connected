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
            # Updated for current uszipcode API (no simple_zipcode kwarg)
            from uszipcode import SearchEngine
            import math, re
            # Simple dataset (default) first
            search_simple = SearchEngine()
            # Comprehensive dataset for fallback when a given zip has no coords in simple DB
            search_full = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)

            user_zip_norm = re.match(r"\d{5}", user_zip or "")
            user_zip_clean = user_zip_norm.group(0) if user_zip_norm else user_zip
            user_zip_obj = search_simple.by_zipcode(user_zip_clean)
            if not (getattr(user_zip_obj, 'lat', None) and getattr(user_zip_obj, 'lng', None)):
                user_zip_obj_full = search_full.by_zipcode(user_zip_clean)
                if user_zip_obj_full and user_zip_obj_full.lat and user_zip_obj_full.lng:
                    user_zip_obj = user_zip_obj_full

            zip_cache = {}

            def get_latlng(z):
                if not z:
                    return None
                m = re.match(r"\d{5}", str(z))
                if not m:
                    return None
                z5 = m.group(0)
                if z5 in zip_cache:
                    return zip_cache[z5]
                zobj = search_simple.by_zipcode(z5)
                if (not zobj or not zobj.lat or not zobj.lng):
                    zobj_full = search_full.by_zipcode(z5)
                    if zobj_full and zobj_full.lat and zobj_full.lng:
                        zobj = zobj_full
                if zobj and zobj.lat and zobj.lng:
                    zip_cache[z5] = (zobj.lat, zobj.lng)
                else:
                    zip_cache[z5] = None
                return zip_cache[z5]

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
                if not user_zip_obj or not getattr(user_zip_obj, 'lat', None) or not getattr(user_zip_obj, 'lng', None):
                    return None
                min_d = None
                for loc in therapist.locations.all():
                    ll = get_latlng(getattr(loc, 'zip', None))
                    if ll and ll[0] and ll[1]:
                        d = haversine(user_zip_obj.lat, user_zip_obj.lng, ll[0], ll[1])
                        if min_d is None or d < min_d:
                            min_d = d
                return round(min_d, 1) if min_d is not None else None

            therapists = list(therapists.distinct())
            for t in therapists:
                t.distance = compute_min_distance(t)

            therapists.sort(key=lambda t: t.distance if t.distance is not None else float('inf'))

            RADIUS = 150  # miles
            within_radius = [t for t in therapists if t.distance is not None and t.distance <= RADIUS]
            if len(within_radius) >= 150:
                therapists = within_radius
            else:
                therapists = (within_radius + [t for t in therapists if t not in within_radius])[:150]
        except Exception as e:
            # Capture the exception reason in DEBUG via attaching attribute (optional)
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
            from uszipcode import SearchEngine
            search_meta = SearchEngine()
            meta_obj = search_meta.by_zipcode(user_zip)
            if meta_obj:
                user_zip_city = getattr(meta_obj, 'major_city', None) or getattr(meta_obj, 'post_office_city', None) or getattr(meta_obj, 'city', None)
                user_zip_state = getattr(meta_obj, 'state', None)
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
        request.session['user_zip'] = zip_code
        return JsonResponse({'status': 'ok', 'zip': zip_code})
    return JsonResponse({'status': 'error', 'message': 'No zip provided'}, status=400)

def geo_zip(request):
    """Return nearest ZIP for provided lat/lon using uszipcode SearchEngine."""
    try:
        lat_raw = request.GET.get('lat', '')
        lng_raw = request.GET.get('lng', '')
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (TypeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid coordinates'}, status=400)
    try:
        from uszipcode import SearchEngine
        debug = []
        try:
            search_simple = SearchEngine()
            results = search_simple.by_coordinates(lat, lng, radius=40, returns=10) or []
            debug.append(f"simple_results={len(results)}")
        except Exception as e1:
            results = []
            debug.append(f"simple_err={e1.__class__.__name__}")
        if not results:
            try:
                search_full = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)
                results = search_full.by_coordinates(lat, lng, radius=60, returns=10) or []
                debug.append(f"full_results={len(results)}")
            except Exception as e2:
                debug.append(f"full_err={e2.__class__.__name__}")
        # Pick first with zipcode
        for z in results:
            for attr in ("zipcode", "zip"):
                zc = getattr(z, attr, None)
                if zc:
                    return JsonResponse({'status': 'ok', 'zip': zc})
        payload = {'status': 'error', 'message': 'No ZIP found for coordinates'}
        if getattr(settings, 'DEBUG', False):
            payload['debug'] = debug
        return JsonResponse(payload, status=404)
    except Exception as e:
        payload = {'status': 'error', 'message': 'Lookup failed'}
        if getattr(settings, 'DEBUG', False):
            payload['exception'] = f"{e.__class__.__name__}: {e}"
        return JsonResponse(payload, status=500)


def home(request):
    user_zip = request.session.get('user_zip')
    DEFAULT_ZIP = "10001"  # Set your default zip code here
    if not user_zip:
        user_zip = DEFAULT_ZIP
        user_zip_is_default = True
    else:
        user_zip_is_default = False

    query = request.GET.get('q', '').strip()
    therapists = TherapistProfile.objects.filter(user__is_active=True, user__onboarding_status='active')
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

    from uszipcode import SearchEngine
    import math
    from users.location_utils import get_primary_location
    search_simple = SearchEngine()
    search_full = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.comprehensive)
    user_zip_obj = search_simple.by_zipcode(user_zip) or search_full.by_zipcode(user_zip)

    def haversine(lat1, lon1, lat2, lon2):
        R = 3958.8
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def get_min_distance(locations):
        if not user_zip_obj or not locations.exists():
            return None
        min_dist = None
        for loc in locations:
            zip_code = getattr(loc, 'zip', None)
            zip_obj = (search_simple.by_zipcode(zip_code) or search_full.by_zipcode(zip_code)) if zip_code else None
            if zip_obj and zip_obj.lat and zip_obj.lng and user_zip_obj.lat and user_zip_obj.lng:
                dist = haversine(user_zip_obj.lat, user_zip_obj.lng, zip_obj.lat, zip_obj.lng)
                if min_dist is None or dist < min_dist:
                    min_dist = dist
        return round(min_dist, 1) if min_dist is not None else None

    therapists = list(therapists)
    for t in therapists:
        t.distance = get_min_distance(t.locations.all())

    therapists_final = sorted(therapists, key=lambda t: t.distance if t.distance is not None else float('inf'))[:6]

    from users.models_featured import FeaturedTherapistHistory, FeaturedBlogPostHistory
    today = timezone.now().date()
    # Try to get today's featured therapist and blog post from history
    featured_therapist_entry = FeaturedTherapistHistory.objects.filter(date=today).first()
    featured_blog_entry = FeaturedBlogPostHistory.objects.filter(date=today).first()
    top_therapist = featured_therapist_entry.therapist if featured_therapist_entry else (therapists_final[0] if therapists_final else None)
    top_blog_post = featured_blog_entry.blog_post if featured_blog_entry else BlogPost.objects.filter(published=True).order_by('-created_at').first()
    # Add city/state meta for current zip
    user_zip_city = None
    user_zip_state = None
    try:
        if user_zip_obj:
            user_zip_city = getattr(user_zip_obj, 'major_city', None) or getattr(user_zip_obj, 'post_office_city', None) or getattr(user_zip_obj, 'city', None)
            user_zip_state = getattr(user_zip_obj, 'state', None)
    except Exception:
        pass
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
