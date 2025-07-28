from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField

# Custom User model for AUTH_USER_MODEL
class User(AbstractUser):
    ONBOARDING_CHOICES = [
        ('pending_email_confirmation', 'Pending Email Confirmation'),
        ('pending_payment', 'Pending Payment'),
        ('pending_profile_completion', 'Pending Profile Completion'),
        ('active', 'Active'),
    ]
    onboarding_status = models.CharField(
        max_length=32,
        choices=ONBOARDING_CHOICES,
        default='pending_email_confirmation',
        help_text='Tracks onboarding progress for the user.'
    )

    def __str__(self):
        return self.email or self.username


class SubscriptionType(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = RichTextField(blank=True)
    stripe_plan_id_monthly = models.CharField(max_length=128, unique=True, null=True, blank=True)
    stripe_plan_id_annual = models.CharField(max_length=128, unique=True, null=True, blank=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_annual = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# Subscription model (top-level)
class Subscription(models.Model):
    INTERVAL_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription_type = models.ForeignKey(SubscriptionType, on_delete=models.PROTECT, null=True, blank=True)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default='monthly')
    stripe_subscription_id = models.CharField(max_length=128, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=128, blank=True, null=True)
    stripe_payment_method_id = models.CharField(max_length=128, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.subscription_type.name} ({self.interval})"

# TherapistProfileStats model for daily stats
class TherapistProfileStats(models.Model):
    therapist = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    search_impressions = models.PositiveIntegerField(default=0)
    search_rank = models.PositiveIntegerField(null=True, blank=True)
    profile_clicks = models.PositiveIntegerField(default=0)
    contact_clicks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('therapist', 'date')

    def __str__(self):
        return f"Stats for {self.therapist.email} on {self.date}"

