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
from users.models_profile import TherapistProfile, PracticeAreaTag
from users.models_blog import BlogPost
from django.utils import timezone
from django.db.models import Q

def therapists_page(request):
    query = request.GET.get('q', '').strip()
    tier = request.GET.get('tier', '').strip()
    specialty = request.GET.get('specialty', '').strip()
    therapists = TherapistProfile.objects.filter(user__is_active=True, user__onboarding_status='active')
    if query:
        q_obj = Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(credentials__icontains=query) | Q(city__icontains=query) | Q(state__icontains=query) | Q(short_bio__icontains=query) | Q(tagline__icontains=query)
        therapists = therapists.filter(q_obj)
    if tier:
        therapists = therapists.filter(license_type__name__iexact=tier)
    if specialty:
        therapists = therapists.filter(practice_areas_tags__id=specialty)

    user_zip = request.session.get('user_zip')
    if user_zip:
        try:
            from uszipcode import SearchEngine
            search = SearchEngine(simple_zipcode=True)
            user_zip_obj = search.by_zipcode(user_zip)
            def get_distance(zip_code):
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and user_zip_obj and zip_obj.lat and zip_obj.lng and user_zip_obj.lat and user_zip_obj.lng:
                    return ((zip_obj.lat - user_zip_obj.lat)**2 + (zip_obj.lng - user_zip_obj.lng)**2) ** 0.5
                return float('inf')
            therapists = list(therapists)
            for t in therapists:
                t.distance = get_distance(t.zip_code)
            therapists = sorted(therapists, key=lambda t: t.distance)
        except Exception:
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

    practice_areas_tags = PracticeAreaTag.objects.all().order_by('name')
    return render(request, 'therapists.html', {
        'therapists': therapists_page_obj,
        'practice_areas_tags': practice_areas_tags,
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
        else:
            if len(terms) > 0:
                city = terms[0]
        # Use uszipcode to get nearby cities within 100 miles
        if city:
            try:
                from uszipcode import SearchEngine
                search = SearchEngine(simple_zipcode=True)
                results = search.by_city_and_state(city, state if state else None)
                if results:
                    zipcodes = [r.zipcode for r in results if r.zipcode]
                    # Get all cities within 100 miles of the first result
                    if zipcodes:
                        nearby = search.query(zipcode=zipcodes[0], radius=100, returns=100)
                        nearby_cities = [(z.major_city, z.state) for z in nearby]
            except Exception:
                nearby_cities = []
        # Build Q for nearby cities
        q_nearby = Q()
        for nc, ns in nearby_cities:
            q_nearby |= Q(city__iexact=nc, state__iexact=ns)
        # Build Q for other terms
        other_terms = [t for t in terms if t.lower() != (city or '').lower() and t.lower() != (state or '').lower()]
        q_other = Q()
        for term in other_terms:
            q_other |= Q(first_name__icontains=term)
            q_other |= Q(last_name__icontains=term)
            q_other |= Q(credentials__icontains=term)
            q_other |= Q(practice_areas_tags__name__icontains=term)
            q_other |= Q(short_bio__icontains=term)
            q_other |= Q(tagline__icontains=term)
        # Prioritize therapists in nearby cities who also match other terms
        if nearby_cities:
            prioritized = list(therapists.filter(q_nearby & q_other).distinct())
            prioritized_ids = {t.id for t in prioritized}
        # Flexible search for all terms
        q_all = Q()
        for term in terms:
            q_all |= Q(first_name__icontains=term)
            q_all |= Q(last_name__icontains=term)
            q_all |= Q(credentials__icontains=term)
            q_all |= Q(city__icontains=term)
            q_all |= Q(state__icontains=term)
            q_all |= Q(practice_areas_tags__name__icontains=term)
            q_all |= Q(short_bio__icontains=term)
            q_all |= Q(tagline__icontains=term)
        others = [t for t in therapists.filter(q_all).distinct() if t.id not in prioritized_ids]
    else:
        others = list(therapists)
    # Combine prioritized and others, keeping order and uniqueness
    combined = prioritized + others
    results = []
    for therapist in combined[:20]:
        card_html = render_to_string('partials/therapist_card.html', {'therapist': therapist})
        results.append({
            'id': therapist.id,
            'card_html': card_html
        })
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
from users.models_profile import TherapistProfile, ZipCode


def home(request):
    user_zip = request.session.get('user_zip')
    therapists = TherapistProfile.objects.filter(user__is_active=True, user__onboarding_status='active')

    if user_zip:
        from uszipcode import SearchEngine
        search = SearchEngine()
        zipcode_obj = search.by_zipcode(user_zip)
        nearby_zips = []
        if zipcode_obj and zipcode_obj.lat and zipcode_obj.lng:
            results = search.query(lat=zipcode_obj.lat, lng=zipcode_obj.lng, radius=50, returns=100)
            nearby_zips = [z.zipcode for z in results]
        therapists_nearby = therapists.filter(zip_code__in=nearby_zips).order_by('-user__last_login')
        count = therapists_nearby.count()
        if count < 6:
            user_zip_obj = search.by_zipcode(user_zip)
            def get_distance(zip_code):
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and user_zip_obj:
                    return ((zip_obj.lat - user_zip_obj.lat)**2 + (zip_obj.lng - user_zip_obj.lng)**2) ** 0.5
                return float('inf')
            other_therapists = therapists.exclude(id__in=therapists_nearby.values_list('id', flat=True)).exclude(zip_code="").all()
            sorted_others = sorted(other_therapists, key=lambda t: get_distance(t.zip_code))
            therapists_final = list(therapists_nearby) + list(sorted_others[:6-count])
        else:
            therapists_final = list(therapists_nearby[:6])
    else:
        therapists_final = list(therapists.order_by('-user__last_login')[:6])

    # Get today's date
    today = timezone.now().date()
    # Top blog post for today (most recent published post from today, fallback to most recent published)
    top_blog_post = BlogPost.objects.filter(published=True, created_at__date=today).order_by('-created_at').first()
    if not top_blog_post:
        top_blog_post = BlogPost.objects.filter(published=True).order_by('-created_at').first()

    # Top therapist for today (most recently active, fallback to first in therapists_final)
    top_therapist = therapists.order_by('-user__last_login').first() or (therapists_final[0] if therapists_final else None)

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
