from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models_profile import TherapistProfile
from users.models_blog import BlogPost
from users.models_featured import FeaturedTherapistHistory, FeaturedBlogPostHistory
import random

class Command(BaseCommand):
    help = 'Rotate daily featured therapist and blog post, ensuring no repeats until all have been featured.'

    def handle(self, *args, **options):
        today = timezone.now().date()

        # --- Therapist ---
        all_therapists = list(TherapistProfile.objects.all())
        featured_therapists = set(FeaturedTherapistHistory.objects.filter(cycle=self.get_current_cycle(FeaturedTherapistHistory)).values_list('therapist_id', flat=True))
        unfeatured_therapists = [t for t in all_therapists if t.id not in featured_therapists]
        if not unfeatured_therapists:
            FeaturedTherapistHistory.objects.all().delete()
            featured_therapists = set()
            unfeatured_therapists = all_therapists
        therapist = random.choice(unfeatured_therapists) if unfeatured_therapists else None
        if therapist:
            FeaturedTherapistHistory.objects.create(therapist=therapist, date=today, cycle=self.get_current_cycle(FeaturedTherapistHistory))
            self.stdout.write(self.style.SUCCESS(f"Featured therapist for {today}: {therapist}"))

        # --- Blog Post ---
        all_posts = list(BlogPost.objects.filter(published=True))
        featured_posts = set(FeaturedBlogPostHistory.objects.filter(cycle=self.get_current_cycle(FeaturedBlogPostHistory)).values_list('blog_post_id', flat=True))
        unfeatured_posts = [p for p in all_posts if p.id not in featured_posts]
        if not unfeatured_posts:
            FeaturedBlogPostHistory.objects.all().delete()
            featured_posts = set()
            unfeatured_posts = all_posts
        post = random.choice(unfeatured_posts) if unfeatured_posts else None
        if post:
            FeaturedBlogPostHistory.objects.create(blog_post=post, date=today, cycle=self.get_current_cycle(FeaturedBlogPostHistory))
            self.stdout.write(self.style.SUCCESS(f"Featured blog post for {today}: {post}"))

    def get_current_cycle(self, model):
        latest = model.objects.order_by('-cycle').first()
        return (latest.cycle + 1) if not model.objects.exists() else (latest.cycle or 1)
