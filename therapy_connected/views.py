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
            # Get zip codes within 50 miles using lat/lng
            results = search.query(lat=zipcode_obj.lat, lng=zipcode_obj.lng, radius=50, returns=100)
            nearby_zips = [z.zipcode for z in results]
        therapists_nearby = therapists.filter(zip_code__in=nearby_zips).order_by('-user__last_login')
        count = therapists_nearby.count()
        if count < 6:
            # Find all therapists with zip codes, calculate distance, and fill with next closest
            from uszipcode import SearchEngine
            search = SearchEngine()
            user_zip_obj = search.by_zipcode(user_zip)
            def get_distance(zip_code):
                zip_obj = search.by_zipcode(zip_code)
                if zip_obj and user_zip_obj:
                    return ((zip_obj.lat - user_zip_obj.lat)**2 + (zip_obj.lng - user_zip_obj.lng)**2) ** 0.5
                return float('inf')
            # Exclude already selected, get all others with zip_code
            other_therapists = therapists.exclude(id__in=therapists_nearby.values_list('id', flat=True)).exclude(zip_code="").all()
            # Sort by distance
            sorted_others = sorted(other_therapists, key=lambda t: get_distance(t.zip_code))
            therapists_final = list(therapists_nearby) + list(sorted_others[:6-count])
        else:
            therapists_final = list(therapists_nearby[:6])
    else:
        therapists_final = list(therapists.order_by('-user__last_login')[:6])

    # Optionally, you could prompt for zip code if not set

    return render(request, 'home.html', {'therapists': therapists_final})

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
