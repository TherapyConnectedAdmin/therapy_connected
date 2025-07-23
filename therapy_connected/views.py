from django.shortcuts import render, redirect
from users.models import SubscriptionType

def home(request):
    return render(request, 'home.html')

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
