from django.core.management.base import BaseCommand
from users.models_blog import BlogPost, BlogTag
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = 'Seed example blog posts and tags.'

    def handle(self, *args, **options):
        User = get_user_model()
        # Use a list of therapist user IDs for authorship
        therapist_ids = [237, 238, 239]
        therapist_users = list(User.objects.filter(id__in=therapist_ids))
        if len(therapist_users) < 3:
            self.stdout.write(self.style.ERROR('Not enough therapist users found to assign as authors.'))
            return

        tag_names = ['Wellness', 'Therapy', 'Mindfulness', 'Self-Care', 'Community']
        tags = []
        for name in tag_names:
            tag, _ = BlogTag.objects.get_or_create(name=name)
            tags.append(tag)

        posts = [
            {
                'title': 'Welcome to the Therapy Connected Blog',
                'content': '<p>Discover the latest in mental health, therapy tips, and community stories. Stay tuned for weekly updates!</p>',
                'tags': [tags[0], tags[1]],
                'image_url': 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=600&q=80',
                'author': therapist_users[0],
            },
            {
                'title': '5 Simple Self-Care Habits for a Calmer Mind',
                'content': '<ul><li>Take a mindful walk</li><li>Practice deep breathing</li><li>Write in a gratitude journal</li><li>Connect with a friend</li><li>Unplug for 30 minutes</li></ul>',
                'tags': [tags[3], tags[2]],
                'image_url': 'https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=600&q=80',
                'author': therapist_users[1],
            },
            {
                'title': 'How Therapy Can Help You Thrive',
                'content': '<p>Therapy is not just for crises. Learn how regular sessions can support your growth, resilience, and happiness.</p>',
                'tags': [tags[1], tags[4]],
                'image_url': 'https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=crop&w=600&q=80',
                'author': therapist_users[2],
            },
        ]

        from django.utils.text import slugify
        import requests
        from django.core.files.base import ContentFile
        for post_data in posts:
            base_slug = slugify(post_data['title'])
            slug = base_slug
            i = 1
            while BlogPost.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            post, created = BlogPost.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': post_data['title'],
                    'author': post_data['author'],
                    'content': post_data['content'],
                    'created_at': timezone.now(),
                    'published': True,
                }
            )
            # If the post already exists, update the author if needed
            if not created and post.author != post_data['author']:
                post.author = post_data['author']
            # Always update tags and image for both new and existing posts
            post.tags.set(post_data['tags'])
            if post_data.get('image_url'):
                try:
                    resp = requests.get(post_data['image_url'])
                    if resp.status_code == 200:
                        img_name = f"{slug}.jpg"
                        post.image.save(img_name, ContentFile(resp.content), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not fetch image: {e}'))
            post.save()
            if created:
                self.stdout.write(self.style.SUCCESS(f'Seeded: {post.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated image/tags for: {post.title}'))
