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
    therapists = TherapistProfile.objects.filter(user__is_active=True, user__onboarding_status='active')
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
    if user_zip:
        try:
            from uszipcode import SearchEngine
            search = SearchEngine(simple_zipcode=True)
            user_zip_obj = search.by_zipcode(user_zip)
            import math
            def haversine(lat1, lon1, lat2, lon2):
                R = 3958.8
                phi1 = math.radians(lat1)
                phi2 = math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return R * c

            def get_distance(zip_code):
                if not zip_code or not user_zip_obj:
                    return None
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and zip_obj.lat and zip_obj.lng and user_zip_obj.lat and user_zip_obj.lng:
                    dist = haversine(user_zip_obj.lat, user_zip_obj.lng, zip_obj.lat, zip_obj.lng)
                    return round(dist, 1)
                return None
            therapists = therapists.distinct()
            therapists = list(therapists)
            from users.location_utils import get_primary_location
            for t in therapists:
                primary_location = get_primary_location(t.locations.all())
                zip_code = getattr(primary_location, 'zip', None) if primary_location else None
                t.distance = get_distance(zip_code)
            therapists = sorted(therapists, key=lambda t: t.distance if t.distance is not None else float('inf'))
        except Exception:
            if not isinstance(therapists, list):
                therapists = therapists.distinct().order_by('-user__last_login')
    else:
        therapists = therapists.distinct().order_by('-user__last_login')

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
            search_meta = SearchEngine(simple_zipcode=True)
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
        # Primary attempt (simple)
        try:
            search = SearchEngine(simple_zipcode=True)
            results = search.by_coordinates(lat, lng, radius=40, returns=10) or []
            debug.append(f"simple_results={len(results)}")
        except Exception as e1:
            results = []
            debug.append(f"simple_err={e1.__class__.__name__}")
        # Fallback (full) if needed
        if not results:
            try:
                search_full = SearchEngine(simple_zipcode=False)
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
            Q(credentials__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query) |
            Q(state__iexact=normalized_query) |
            Q(short_bio__icontains=query) |
            Q(tagline__icontains=query)
        )
        therapists = therapists.filter(q_obj)

    from uszipcode import SearchEngine
    import math
    from users.location_utils import get_primary_location
    search = SearchEngine()
    user_zip_obj = search.by_zipcode(user_zip)

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
            zip_obj = search.by_zipcode(zip_code) if zip_code else None
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
