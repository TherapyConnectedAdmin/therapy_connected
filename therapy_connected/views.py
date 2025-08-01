# About page view
def about_page(request):
    return render(request, 'about.html')
# Pricing page view
from users.models import SubscriptionType
def pricing_page(request):
    plans = SubscriptionType.objects.filter(active=True).order_by('price_monthly')
    return render(request, 'pricing.html', {'plans': plans})
from django.shortcuts import render
# Features page view
def features_page(request):
    return render(request, 'features.html')
from users.models_profile import TherapistProfile
from users.models_blog import BlogPost
from django.utils import timezone
from django.db.models import Q
from users.models import TherapistProfileStats

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

    return render(request, 'therapists.html', {
        'therapists': therapists_page_obj,
        'paginator': paginator,
        'page_obj': therapists_page_obj,
    })
from django.http import JsonResponse
from django.template.loader import render_to_string
from users.models_profile import TherapistProfile
# Search therapists API for homepage modal
def search_therapists(request):
    query = request.GET.get('q', '').strip()
    therapists = TherapistProfile.objects.all()
    prioritized = []
    others = []
    prioritized_ids = set()
    if query:
        from django.db.models import Q
        import re
        city_state_match = re.match(r"([A-Za-z .'-]+),?\s*([A-Za-z]{2})$", query)
        terms = [t for t in query.split() if t]
        city = None
        state = None
        nearby_cities = []
        if city_state_match:
            city = city_state_match.group(1).strip()
            state = city_state_match.group(2).strip().upper()
    if query:
        from django.db.models import Q
        from users.utils.state_normalize import normalize_state
        import re
        city_state_match = re.match(r"([A-Za-z .'-]+),?\s*([A-Za-z]{2,})$", query)
        terms = [t for t in query.split() if t]
        city = None
        state = None
        nearby_cities = []
        if city_state_match:
            city = city_state_match.group(1).strip()
            state = normalize_state(city_state_match.group(2).strip())
        else:
            if len(terms) > 0:
                city = terms[0]
        # Use uszipcode to get nearby cities within 100 miles
    if query:
        from django.db.models import Q
        from users.utils.state_normalize import normalize_state
        import re
        city_state_match = re.match(r"([A-Za-z .'-]+),?\s*([A-Za-z]{2,})$", query)
        terms = [t for t in query.split() if t]
        city = None
        state = None
        nearby_cities = []
        normalized_query = normalize_state(query)
        if city_state_match:
            city = city_state_match.group(1).strip()
            state = normalize_state(city_state_match.group(2).strip())
        else:
            if len(terms) > 0:
                city = terms[0]
        # Add normalization to Q for direct state search
        q_obj = (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(credentials__license_type__name__icontains=query) |
            Q(credentials__license_type__description__icontains=query) |
            Q(locations__city__icontains=query) |
            Q(locations__state__icontains=query) |
            Q(locations__state__iexact=normalized_query) |
            Q(intro_statement__icontains=query)
        )
        therapists = therapists.filter(q_obj)
        for nc, ns in nearby_cities:
            q_nearby |= Q(city__iexact=nc, state__iexact=ns)
        # Build Q for other terms
        other_terms = [t for t in terms if t.lower() != (city or '').lower() and t.lower() != (state or '').lower()]
        q_other = Q()
        for term in other_terms:
            q_other |= Q(first_name__icontains=term)
            q_other |= Q(last_name__icontains=term)
            q_other |= Q(credentials__license_type__name__icontains=term)
            q_other |= Q(credentials__license_type__description__icontains=term)
            q_other |= Q(locations__city__icontains=term)
            q_other |= Q(locations__state__icontains=term)
            q_other |= Q(intro_statement__icontains=term)
        # Prioritize therapists in nearby cities who also match other terms
        if nearby_cities:
            prioritized = list(therapists.filter(q_nearby & q_other).distinct())
            prioritized_ids = {t.id for t in prioritized}
        # Flexible search for all terms
        from users.utils.state_normalize import normalize_state
        q_all = Q()
        for term in terms:
            normalized_term = normalize_state(term)
            q_all |= Q(first_name__icontains=term)
            q_all |= Q(last_name__icontains=term)
            q_all |= Q(credentials__license_type__name__icontains=term)
            q_all |= Q(credentials__license_type__description__icontains=term)
            q_all |= Q(locations__city__icontains=term)
            q_all |= Q(locations__state__icontains=term)
            q_all |= Q(locations__state__iexact=normalized_term)
            q_all |= Q(intro_statement__icontains=term)
        others = [t for t in therapists.filter(q_all).distinct() if t.id not in prioritized_ids]
    else:
        others = list(therapists)
    # Combine prioritized and others, keeping order and uniqueness
    combined = prioritized + others
    # Distance logic: if user_zip is set, calculate and sort by distance
    user_zip = request.session.get('user_zip')
    if user_zip:
        try:
            from uszipcode import SearchEngine
            import math
            from users.location_utils import get_primary_location
            search = SearchEngine(simple_zipcode=True)
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
            def get_distance(zip_code):
                if not zip_code or not user_zip_obj:
                    return None
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and zip_obj.lat and zip_obj.lng and user_zip_obj.lat and user_zip_obj.lng:
                    dist = haversine(user_zip_obj.lat, user_zip_obj.lng, zip_obj.lat, zip_obj.lng)
                    return round(dist, 1)
                return None
            for t in combined:
                primary_location = get_primary_location(t.locations.all())
                zip_code = getattr(primary_location, 'zip', None) if primary_location else None
                t.distance = get_distance(zip_code)
            combined = sorted(combined, key=lambda t: t.distance if t.distance is not None else float('inf'))
        except Exception:
            pass
    results = []
    today = timezone.now().date()
    for idx, therapist in enumerate(combined[:20], start=1):
        card_html = render_to_string('partials/therapist_card.html', {'therapist': therapist})
        results.append({
            'id': therapist.id,
            'card_html': card_html
        })
        # Log search impression and rank
        stats, _ = TherapistProfileStats.objects.get_or_create(therapist=therapist.user, date=today)
        stats.search_impressions += 1
        stats.search_rank = idx  # last rank seen for today
        stats.save()
    return JsonResponse({'results': results})
from django.http import JsonResponse
def set_zip(request):
    zip_code = request.GET.get('zip')
    if zip_code:
        request.session['user_zip'] = zip_code
        return JsonResponse({'status': 'ok', 'zip': zip_code})
    return JsonResponse({'status': 'error', 'message': 'No zip provided'}, status=400)
from django.shortcuts import render, redirect
from users.models import SubscriptionType
from users.models_profile import TherapistProfile


def home(request):
    user_zip = request.session.get('user_zip')
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

    if user_zip:
        from uszipcode import SearchEngine
        search = SearchEngine()
        zipcode_obj = search.by_zipcode(user_zip)
        nearby_zips = []
        if zipcode_obj and zipcode_obj.lat and zipcode_obj.lng:
            results = search.query(lat=zipcode_obj.lat, lng=zipcode_obj.lng, radius=50, returns=100)
            nearby_zips = [z.zipcode for z in results]
        therapists_nearby = therapists.filter(locations__zip__in=nearby_zips).order_by('-user__last_login')
        count = therapists_nearby.count()
        if count < 6:
            user_zip_obj = search.by_zipcode(user_zip)
            def get_distance(zip_code):
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and user_zip_obj:
                    return ((zip_obj.lat - user_zip_obj.lat)**2 + (zip_obj.lng - user_zip_obj.lng)**2) ** 0.5
                return float('inf')
            other_therapists = therapists.exclude(id__in=therapists_nearby.values_list('id', flat=True)).exclude(locations__zip="").all()
            sorted_others = sorted(other_therapists, key=lambda t: get_distance(t.locations.first().zip if t.locations.exists() else ""))
            therapists_final = list(therapists_nearby) + list(sorted_others[:6-count])
        else:
            therapists_final = list(therapists_nearby[:6])
    else:
        therapists_final = list(therapists.order_by('-user__last_login')[:6])

    from users.models_featured import FeaturedTherapistHistory, FeaturedBlogPostHistory
    today = timezone.now().date()
    # Try to get today's featured therapist and blog post from history
    featured_therapist_entry = FeaturedTherapistHistory.objects.filter(date=today).first()
    featured_blog_entry = FeaturedBlogPostHistory.objects.filter(date=today).first()
    top_therapist = featured_therapist_entry.therapist if featured_therapist_entry else (therapists.order_by('-user__last_login').first() or (therapists_final[0] if therapists_final else None))
    top_blog_post = featured_blog_entry.blog_post if featured_blog_entry else BlogPost.objects.filter(published=True).order_by('-created_at').first()

    # Calculate and set distance for all therapists in therapists_final
    user_zip = request.session.get('user_zip')
    if user_zip:
        try:
            from uszipcode import SearchEngine
            import math
            from users.location_utils import get_primary_location
            search = SearchEngine(simple_zipcode=True)
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
            def get_distance(zip_code):
                if not zip_code or not user_zip_obj:
                    return None
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and zip_obj.lat and zip_obj.lng and user_zip_obj.lat and user_zip_obj.lng:
                    dist = haversine(user_zip_obj.lat, user_zip_obj.lng, zip_obj.lat, zip_obj.lng)
                    return round(dist, 1)
                return None
            for t in therapists_final:
                primary_location = get_primary_location(t.locations.all())
                zip_code = getattr(primary_location, 'zip', None) if primary_location else None
                t.distance = get_distance(zip_code)
            therapists_final = sorted(therapists_final, key=lambda t: t.distance if t.distance is not None else float('inf'))
        except Exception:
            pass
    return render(request, 'home.html', {
        'therapists': therapists_final,
        'top_blog_post': top_blog_post,
        'top_therapist': top_therapist,
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
