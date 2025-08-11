"""Generate fake blog tags and posts.
Run with: python manage.py shell < scripts/generate_fake_blog_posts.py
"""
import os, django, random, uuid, tempfile
from faker import Faker
import requests
from django.core.files import File
os.environ.setdefault('DJANGO_SETTINGS_MODULE','therapy_connected.settings')
django.setup()
from django.contrib.auth import get_user_model
from users.models_blog import BlogPost, BlogTag

fake = Faker()
User = get_user_model()

NUM_POSTS = int(os.environ.get('FAKE_NUM_BLOG_POSTS','20'))
NUM_TAGS = int(os.environ.get('FAKE_NUM_BLOG_TAGS','8'))
FAKE_FETCH_BLOG_IMAGES = bool(int(os.environ.get('FAKE_FETCH_BLOG_IMAGES','1')))
BLOG_IMAGE_WIDTH = int(os.environ.get('FAKE_BLOG_IMAGE_WIDTH','900'))
BLOG_IMAGE_HEIGHT = int(os.environ.get('FAKE_BLOG_IMAGE_HEIGHT','600'))
FAKE_RANDOM_SEED = os.environ.get('FAKE_RANDOM_SEED')
if FAKE_RANDOM_SEED:
    random.seed(FAKE_RANDOM_SEED)
    Faker.seed(int(FAKE_RANDOM_SEED))

# Ensure at least one active author (choose or create)
authors = list(User.objects.filter(is_active=True)[:10])
if not authors:
    # create a simple author user
    u = User.objects.create_user(username='author@example.com', email='author@example.com', password='password123')
    u.is_active=True; u.save()
    authors = [u]

# Create / reuse tags
existing_tags = list(BlogTag.objects.all())
while len(existing_tags) < NUM_TAGS:
    name = fake.word().lower()[:32]
    if not BlogTag.objects.filter(name=name).exists():
        existing_tags.append(BlogTag.objects.create(name=name))

# Optionally purge existing posts (env flag)
if os.environ.get('FAKE_CLEAR_BLOG','0') == '1':
    BlogPost.objects.all().delete()

for i in range(NUM_POSTS):
    title = fake.sentence(nb_words=6).rstrip('.')
    slug_base = '-'.join(title.lower().split())[:180]
    slug = slug_base
    suffix = 1
    while BlogPost.objects.filter(slug=slug).exists():
        slug = f"{slug_base}-{suffix}"
        suffix += 1
    content_paras = [fake.paragraph(nb_sentences=random.randint(3,6)) for _ in range(random.randint(3,7))]
    content = '\n\n'.join(content_paras)
    author = random.choice(authors)
    post = BlogPost.objects.create(
        title=title,
        slug=slug,
        content=content[:8000],
        author=author,
        published=random.random()<0.8,
    )
    if FAKE_FETCH_BLOG_IMAGES:
        # Use picsum with deterministic seed so reruns stable unless purged
        seed = uuid.uuid4().hex[:16]
        img_url = f"https://picsum.photos/seed/{seed}/{BLOG_IMAGE_WIDTH}/{BLOG_IMAGE_HEIGHT}.jpg"
        try:
            resp = requests.get(img_url, timeout=10)
            if resp.status_code == 200 and resp.headers.get('Content-Type','').startswith('image'):
                tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                tmp.write(resp.content)
                tmp.flush()
                post.image.save(f"blog_{slug}.jpg", File(tmp), save=True)
        except Exception:
            pass
    # assign 1-3 tags
    tags_for_post = random.sample(existing_tags, k=random.randint(1, min(3, len(existing_tags))))
    post.tags.set(tags_for_post)

print(f"Created/updated {NUM_POSTS} blog posts. Total now: {BlogPost.objects.count()}.")
