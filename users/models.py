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


# --- Social / Members area models ---
class FeedPost(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('members', 'Members'),
        ('connections', 'Connections'),
    ]
    POST_TYPE_CHOICES = [
        ('text', 'Text'),
        ('photo', 'Photo'),
        ('video', 'Video'),
        ('event', 'Event'),
        ('celebrate', 'Celebrate'),
    ]
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default='members')
    # Post composition and scheduling
    post_type = models.CharField(max_length=16, choices=POST_TYPE_CHOICES, default='text')
    title = models.CharField(max_length=200, blank=True, null=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    # Event-specific optional fields
    event_start_at = models.DateTimeField(blank=True, null=True)
    event_location = models.CharField(max_length=255, blank=True, null=True)
    event_url = models.URLField(blank=True, null=True)
    # Celebrate-specific optional fields
    celebrate_type = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feed by {self.author.email} @ {self.created_at:%Y-%m-%d}"


class FeedMedia(models.Model):
    TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='feed_media/%Y/%m/')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    meta = models.JSONField(blank=True, null=True, default=dict)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media {self.type} for post {self.post_id}"


class FeedReaction(models.Model):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('celebrate', 'Celebrate'),
        ('support', 'Support'),
        ('insightful', 'Insightful'),
        ('love', 'Love'),
    ]
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_reactions')
    reaction = models.CharField(max_length=16, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user_id}:{self.reaction} on {self.post_id}"


class FeedComment(models.Model):
    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feed_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author_id} on post {self.post_id}"


class Connection(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked'),
    ]
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_sent')
    addressee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_received')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('requester', 'addressee')

    def __str__(self):
        return f"{self.requester.email} -> {self.addressee.email} ({self.status})"

