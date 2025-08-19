from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

import os
import random
import runpy
import tempfile
import uuid

from django.core.files import File

from users.models import SubscriptionType, Subscription, FeedPost, FeedMedia, FeedComment, FeedReaction, Connection
from users.models_profile import TherapistProfile, ZipCode


class Command(BaseCommand):
    help = "Seed the database with demo data: lookups, zip codes, plans, therapists, blogs, feed, connections."

    def add_arguments(self, parser):
        # Intentionally no required args; provide a couple of optional environment-controlled toggles only.
        parser.add_argument('--skip-migrate', action='store_true', help='Skip running migrate first (default runs migrate).')
        parser.add_argument('--therapists', type=int, default=int(os.environ.get('SEED_THERAPIST_COUNT', '24')), help='How many therapists to create (default 24).')
        parser.add_argument('--blogs', type=int, default=int(os.environ.get('SEED_BLOG_COUNT', '16')), help='How many blog posts to create (default 16).')
        parser.add_argument('--fetch-media', action='store_true', help='Download images for therapists/blog/feed (default off).')

    def handle(self, *args, **opts):
        fetch_media = bool(opts.get('fetch_media'))
        therapist_count = opts['therapists']
        blog_count = opts['blogs']

        # 1) Ensure DB is migrated
        if not opts['skip_migrate']:
            self.stdout.write("Applying migrations …")
            call_command('migrate', interactive=False, verbosity=1)

        # 2) Seed lookups (runs idempotently)
        self.stdout.write("Seeding lookup tables …")
        try:
            runpy.run_path(os.path.abspath(os.path.join(os.getcwd(), 'seed_lookups.py')))
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Lookup seed script raised: {e}"))

        # 3) Seed ZipCode table if empty (small public CSV)
        if ZipCode.objects.count() == 0:
            self.stdout.write("ZipCode empty; loading public subset …")
            try:
                call_command('seed_zipcodes', '--limit', '5000')
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Zip seed failed: {e}"))
        else:
            self.stdout.write("ZipCode table already populated; skipping zip seed.")

        # 4) Upsert SubscriptionType plans (no Stripe calls; use env overrides when provided)
        self.stdout.write("Upserting subscription plans …")
        plans = [
            {
                'name': 'Starter',
                'price_monthly': '19.00',
                'price_annual': '190.00',
                'stripe_plan_id_monthly': os.environ.get('STRIPE_PLAN_STARTER_MONTHLY'),
                'stripe_plan_id_annual': os.environ.get('STRIPE_PLAN_STARTER_ANNUAL'),
                'active': True,
            },
            {
                'name': 'Pro',
                'price_monthly': '39.00',
                'price_annual': '390.00',
                'stripe_plan_id_monthly': os.environ.get('STRIPE_PLAN_PRO_MONTHLY'),
                'stripe_plan_id_annual': os.environ.get('STRIPE_PLAN_PRO_ANNUAL'),
                'active': True,
            },
        ]
        for p in plans:
            obj, created = SubscriptionType.objects.get_or_create(
                name=p['name'],
                defaults={
                    'price_monthly': p['price_monthly'],
                    'price_annual': p['price_annual'],
                    'stripe_plan_id_monthly': p['stripe_plan_id_monthly'],
                    'stripe_plan_id_annual': p['stripe_plan_id_annual'],
                    'active': p['active'],
                }
            )
            changed = False
            if str(obj.price_monthly or '') != str(p['price_monthly']):
                obj.price_monthly = p['price_monthly']; changed = True
            if str(obj.price_annual or '') != str(p['price_annual']):
                obj.price_annual = p['price_annual']; changed = True
            # Only set Stripe IDs if provided via env (keep existing otherwise)
            spm = p.get('stripe_plan_id_monthly')
            spa = p.get('stripe_plan_id_annual')
            if spm and obj.stripe_plan_id_monthly != spm:
                obj.stripe_plan_id_monthly = spm; changed = True
            if spa and obj.stripe_plan_id_annual != spa:
                obj.stripe_plan_id_annual = spa; changed = True
            if obj.active != p['active']:
                obj.active = p['active']; changed = True
            if changed:
                obj.save()
            self.stdout.write(("Created" if created else "Updated") + f" plan: {obj.name}")

        # 5) Seed therapists (adult faces, realistic data). Use existing command.
        self.stdout.write(f"Seeding {therapist_count} therapists …")
        try:
            args = ['--count', str(therapist_count), '--adult-only']
            if fetch_media:
                args.append('--fetch-media')
            call_command('seed_fake_therapists', *args)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Therapist seeding failed: {e}"))

        # 6) Seed blog posts with topic-relevant images
        self.stdout.write(f"Seeding {blog_count} blog posts …")
        try:
            args = ['--count', str(blog_count), '--publish']
            if fetch_media:
                args += ['--fetch-images', '--allow-placeholder']
            call_command('seed_fake_blog_posts', *args)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Blog seeding failed: {e}"))

        # 7) Seed feed posts, media, reactions, comments, and connections among therapists
        self.stdout.write("Seeding feed activity and connections …")
        self._seed_feed_and_connections(fetch_media=fetch_media)

        self.stdout.write(self.style.SUCCESS("All demo data seeded."))

    @transaction.atomic
    def _seed_feed_and_connections(self, fetch_media: bool = False):
        User = get_user_model()
        # Build a pool of therapist users
        t_users = list(User.objects.filter(therapistprofile__isnull=False).order_by('id')[:200])
        if len(t_users) < 2:
            self.stdout.write("Not enough therapist users to seed feed and connections; skipping.")
            return

        # Create a modest number of feed posts
        num_posts = min(40, max(10, len(t_users) * 2))
        created_posts = []
        for i in range(num_posts):
            author = random.choice(t_users)
            content = self._random_paragraph()
            post = FeedPost.objects.create(
                author=author,
                content=content,
                visibility=random.choice(['public', 'members', 'connections']),
                post_type=random.choice(['text', 'photo']),
                is_published=True,
                published_at=timezone.now(),
            )
            created_posts.append(post)
            # Optionally attach an image
            if fetch_media and post.post_type == 'photo':
                try:
                    import requests
                    img_url = f"https://picsum.photos/seed/{uuid.uuid4().hex[:10]}/1200/800.jpg"
                    resp = requests.get(img_url, timeout=12)
                    if resp.status_code == 200 and resp.headers.get('Content-Type','').startswith('image'):
                        tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                        tmp.write(resp.content); tmp.flush()
                        FeedMedia.objects.create(post=post, type='image', file=File(tmp, name=f"feed_{post.id}.jpg"))
                except Exception:
                    pass

        # Reactions and comments
        reactions = ['like', 'celebrate', 'support', 'insightful', 'love', 'laugh']
        for post in created_posts:
            # a few reactions from distinct users
            for user in random.sample(t_users, k=min(len(t_users), random.randint(0, 5))):
                try:
                    FeedReaction.objects.get_or_create(post=post, user=user, defaults={'reaction': random.choice(reactions)})
                except Exception:
                    continue
            # 0-2 comments
            for _ in range(random.randint(0, 2)):
                commenter = random.choice(t_users)
                FeedComment.objects.create(post=post, author=commenter, content=self._random_short_sentence())

        # Connections: form a simple ring of accepted connections, plus some pendings
        for i in range(len(t_users)):
            a = t_users[i]
            b = t_users[(i + 1) % len(t_users)]
            if a.id == b.id:
                continue
            # Ensure requester<->addressee uniqueness order
            if not Connection.objects.filter(requester=a, addressee=b).exists() and not Connection.objects.filter(requester=b, addressee=a).exists():
                Connection.objects.create(requester=a, addressee=b, status='accepted')
        # Random pending invites
        for _ in range(min(20, len(t_users))):
            a, b = random.sample(t_users, 2)
            if not Connection.objects.filter(requester=a, addressee=b).exists() and not Connection.objects.filter(requester=b, addressee=a).exists():
                Connection.objects.create(requester=a, addressee=b, status='pending')

    def _random_paragraph(self) -> str:
        sentences = [
            "Reflecting on practice growth and sustainable pacing.",
            "Honoring culture, identity, and context in clinical work.",
            "Integrating evidence-based skills with human connection.",
            "Small changes add up—track process, not perfection.",
            "Boundaries support compassion and endurance.",
            "Psychoeducation can empower without pathologizing.",
        ]
        return ' '.join(random.sample(sentences, k=random.randint(2, 4)))

    def _random_short_sentence(self) -> str:
        fragments = [
            "Love this.",
            "So well said.",
            "Saving this for later.",
            "Appreciate the framing.",
            "Great reminder—thank you.",
        ]
        return random.choice(fragments)
