from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from django.db.models import Q
from faker import Faker
from users.models_blog import BlogPost, BlogTag
import random, uuid, requests, tempfile, os, time
from django.core.files import File
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

fake = Faker()
User = get_user_model()

PRACTICE_TOPICS = [
    ("Building a Sustainable Private Practice", ["practice", "business", "sustainability"], ["private practice", "business model", "ethical growth"]),
    ("Effective Documentation Strategies in Therapy", ["documentation", "notes"], ["clinical notes", "soap notes", "risk management"]),
    ("Marketing Your Therapy Practice Authentically", ["marketing", "authentic"], ["ethical marketing", "referrals", "branding"]),
    ("Navigating Insurance Billing and Reimbursement", ["insurance", "billing"], ["claims", "reimbursement", "eligibility"]),
    ("Telehealth Setup: Tools, Workflow, and Presence", ["telehealth", "technology"], ["virtual sessions", "HIPAA", "online therapy"]),
    ("Pricing Your Services: Sliding Scales and Value", ["pricing", "fees"], ["sliding scale", "value based", "transparency"]),
    ("Ethical Considerations in Digital Mental Health", ["ethics", "digital"], ["telehealth ethics", "privacy", "informed consent"]),
]

CLINICAL_TOPICS = [
    ("Understanding and Treating Generalized Anxiety", ["anxiety", "calm"], ["CBT", "worry cycle", "psychoeducation"]),
    ("A Modern Approach to Depression Care", ["depression", "mood"], ["behavioral activation", "rumination", "hope"],),
    ("Supporting Clients with ADHD: Structure and Compassion", ["adhd", "focus"], ["executive function", "skill building", "acceptance"]),
    ("Working with OCD: Exposure with Humanity", ["ocd", "exposure"], ["ERP", "rituals", "anxiety tolerance"]),
    ("PTSD and the Window of Tolerance", ["ptsd", "trauma"], ["grounding", "somatic", "memory processing"]),
    ("Addressing Burnout in High Achievers", ["burnout", "energy"], ["perfectionism", "rest", "values alignment"]),
    ("Integrating Somatic Techniques in Talk Therapy", ["somatic", "mind-body"], ["regulation", "interoception", "polyvagal"]),
    ("Therapeutic Work with Grief and Ambiguous Loss", ["grief", "loss"], ["meaning making", "ritual", "compassion"]),
]

RELATIONSHIP_TOPICS = [
    ("Strengthening Couples Communication Patterns", ["couples", "communication"], ["attachment", "repair", "conflict de-escalation"]),
    ("Group Therapy Dynamics: Safety and Growth", ["group", "therapy"], ["cohesion", "process", "norms"]),
]

THERAPIST_WELLNESS_TOPICS = [
    ("Clinician Self-Care Beyond Bubble Baths", ["self-care", "therapist"], ["boundaries", "vicarious trauma", "rest"]),
    ("Preventing Compassion Fatigue Early", ["compassion", "fatigue"], ["resilience", "monitoring", "support"]),
]

ALL_TOPICS = PRACTICE_TOPICS + CLINICAL_TOPICS + RELATIONSHIP_TOPICS + THERAPIST_WELLNESS_TOPICS

DISCLAIMER = ("This article is for educational purposes only and does not replace professional training, supervision, or individualized clinical judgment."
              " Clients should consult a qualified professional for personal mental health concerns.")

INTRO_TEMPLATES = [
    "{title} is a recurring theme in modern mental health work. Clinicians and clients alike benefit from clearer language, compassionate framing, and pragmatic tools.",
    "In this post we explore {title_lower}—why it matters, how to conceptualize it, and actionable strategies you can begin adapting today.",
    "The landscape around {title_lower} continues to evolve. Let’s unpack current thinking and translate insight into grounded clinical practice.",
]

SECTION_TEMPLATES = [
    ("Context & Core Concepts", "We start by clarifying key terms, common myths, and the frameworks that guide ethical intervention. {concepts}"),
    ("Assessment & Formulation", "Accurate, compassionate assessment prevents premature pathologizing. Consider function, developmental history, cultural context, and presenting patterns."),
    ("Intervention Strategies", "An integrative, evidence-informed toolkit balances structure with flexibility. Emphasize collaboration, pacing, and skill generalization."),
    ("Ethics & Cultural Humility", "Intersectionality, access, and narrative shape how this issue manifests. Ongoing reflection helps reduce inadvertent harm and enhances alliance."),
    ("Practical Takeaways", "Distill insights into micro-interventions, reflective prompts, and process goals you can fold into documentation and supervision."),
]

CLOSING_TEMPLATES = [
    "Effective work with {title_lower} blends attunement, structured methods, and a willingness to adjust in real time.",
    "Sustainable growth requires iterative reflection—return to your case notes, outcomes, and client feedback loops.",
    "Small, well-scaffolded shifts accumulate. Track process markers, not perfection, as you integrate these ideas.",
]

IMAGE_QUERY_FALLBACKS = ["mental-health", "therapy", "counseling", "mindfulness", "psychology"]


def build_content(title: str, keywords_display: str, concepts: str) -> str:
    title_lower = title.lower()
    intro = random.choice(INTRO_TEMPLATES).format(title=title, title_lower=title_lower)
    sections = []
    for heading, body_template in SECTION_TEMPLATES:
        body = body_template.format(concepts=concepts)
        sections.append(f"## {heading}\n\n{body}\n")
    closing = random.choice(CLOSING_TEMPLATES).format(title_lower=title_lower)
    bullet_block = "\n".join([f"- {p}" for p in [
        f"Define success metrics for {keywords_display}",
        "Co-create language with clients (shared formulation)",
        "Track process + outcome (not just symptom) markers",
        "Integrate reflective pauses in-session",
        "Iterate ethically: feedback, adjust, document"
    ]])
    return f"{intro}\n\n{DISCLAIMER}\n\n{''.join(sections)}\n### Implementation Checklist\n\n{bullet_block}\n\n### Closing Thoughts\n\n{closing}\n"


def pick_image_url(primary_keywords, secondary_keywords):
    """Return a topic-relevant image URL (Unsplash source) or fallback."""
    base = os.environ.get("BLOG_IMAGE_SOURCE", "unsplash").lower()
    # Compose query string with 1-2 strong keywords; fall back to generic mental-health
    candidates = [*primary_keywords[:2], *(secondary_keywords[:1])]
    candidates = [c for c in candidates if c]
    if not candidates:
        candidates = IMAGE_QUERY_FALLBACKS
    query = ",".join(candidates[:2])
    if base == "unsplash":
        # Unsplash source returns a random photo per request matching query
        return f"https://source.unsplash.com/1200x800/?{query}"
    # Generic fallback (picsum not topic aware)
    seed = uuid.uuid4().hex[:10]
    return f"https://picsum.photos/seed/{seed}/1200/800.jpg"


def unique_slug(title: str) -> str:
    base = slugify(title) or f"post-{uuid.uuid4().hex[:8]}"
    slug = base
    i = 2
    while BlogPost.objects.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def ensure_author_pool(min_size: int = 3):
    """Return a list of non-superuser authors; create seed authors if none.

    Ensures we NEVER use the admin/superuser account for seeded blog content
    and provides a small pool so authorship looks varied.
    """
    authors = list(User.objects.filter(is_superuser=False).order_by('id'))
    if not authors:
        # create a small pool of seed authors
        for i in range(min_size):
            email = f"editor{i+1}.{uuid.uuid4().hex[:6]}@example.com"
            authors.append(User.objects.create_user(username=email, email=email, password="password123"))
    return authors


def ensure_tags(tag_strings):
    tags = []
    for t in tag_strings:
        slug = slugify(t)[:32]
        obj, _ = BlogTag.objects.get_or_create(name=t[:32])
        tags.append(obj)
    return tags

class Command(BaseCommand):
    help = "Seed fake mental-health focused blog posts with topic-relevant images."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='Number of posts to create')
        parser.add_argument('--purge', action='store_true', help='Delete existing generated posts (identified by example.com editor or slug prefix)')
        parser.add_argument('--fetch-images', action='store_true', help='Attempt to download and attach topic images')
        parser.add_argument('--publish', action='store_true', help='Mark posts as published')
        parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
        parser.add_argument('--backfill-missing-images', action='store_true', help='Only fetch images for existing posts that lack one (no new posts created)')
        parser.add_argument('--image-retries', type=int, default=3, help='Retries per post for fetching an image (with fallbacks)')
        parser.add_argument('--verbose-images', action='store_true', help='Log per-attempt image fetch details')
        parser.add_argument('--allow-placeholder', action='store_true', help='Generate a local placeholder if remote image fetch fails')

    @transaction.atomic
    def handle(self, *args, **opts):
        count = opts['count']
        purge = opts['purge']
        fetch_images = opts['fetch_images']
        backfill_only = opts['backfill_missing_images']
        publish = opts['publish']
        seed = opts.get('seed')
        image_retries = max(1, opts['image_retries'])
        verbose_images = opts['verbose_images']
        allow_placeholder = opts['allow_placeholder']
        if seed is not None:
            random.seed(seed); Faker.seed(seed)
        if purge:
            topic_titles = [t[0] for t in ALL_TOPICS]
            qs = BlogPost.objects.filter(
                Q(author__email__icontains='editor.') | Q(title__in=topic_titles)
            )
            deleted = qs.count()
            qs.delete()
            self.stdout.write(self.style.WARNING(f"Purged {deleted} existing seeded/topic-matching posts"))

        def generate_placeholder(post, primary_kw):
            """Create a simple local placeholder (1200x800) with title + keywords text."""
            try:
                W, H = 1200, 800
                img = Image.new('RGB', (W, H), color=(35, 61, 82))
                draw = ImageDraw.Draw(img)
                title_text = (post.title[:42] + '…') if len(post.title) > 43 else post.title
                kw_text = ", ".join(primary_kw[:2])
                body_text = f"{title_text}\n{kw_text}" if kw_text else title_text
                try:
                    font = ImageFont.truetype('Arial.ttf', 50)
                except Exception:
                    font = ImageFont.load_default()
                lines = body_text.split('\n')
                metrics = []
                total_h = 0
                for line in lines:
                    x0, y0, x1, y1 = draw.textbbox((0,0), line, font=font)
                    w, h = x1 - x0, y1 - y0
                    metrics.append((line, w, h))
                    total_h += h + 12
                y = (H - total_h)//2
                for line, w, h in metrics:
                    x = (W - w)//2
                    draw.text((x, y), line, fill=(255,255,255), font=font)
                    y += h + 12
                bio = BytesIO()
                img.save(bio, format='JPEG', quality=85)
                return ContentFile(bio.getvalue(), name=f"blog_{post.slug}_ph.jpg")
            except Exception as e:
                if verbose_images:
                    self.stdout.write(f"    Placeholder generation failed: {e}")
            return None

        def fetch_and_attach_image(post, primary_kw, secondary_kw):
            if not fetch_images or post.image:
                return False
            attempt = 0
            kw_pairs = []
            base_primary = primary_kw[:2]
            base_secondary = secondary_kw[:2]
            if base_primary:
                kw_pairs.append(base_primary)
            if base_primary and base_secondary:
                kw_pairs.append([base_primary[0], base_secondary[0]])
            kw_pairs.append(IMAGE_QUERY_FALLBACKS[:2])
            saved = False
            while attempt < image_retries and not saved:
                attempt += 1
                pair = kw_pairs[min(attempt-1, len(kw_pairs)-1)]
                img_url = pick_image_url(pair, [])
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; TCSeedBot/1.0)', 'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'}
                try:
                    resp = requests.get(img_url, timeout=25, headers=headers)
                    ctype = resp.headers.get('Content-Type','')
                    ok = resp.status_code == 200 and ctype.startswith('image') and resp.content and len(resp.content) > 1024
                    if verbose_images:
                        self.stdout.write(f"    Image attempt {attempt} url={img_url} status={resp.status_code} ctype={ctype} ok={ok}")
                    if ok:
                        tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                        tmp.write(resp.content)
                        tmp.flush()
                        post.image.save(f"blog_{post.slug}.jpg", File(tmp), save=True)
                        saved = True
                        break
                except Exception as e:
                    if verbose_images:
                        self.stdout.write(f"    Image attempt {attempt} exception: {e}")
                time.sleep(0.35)
            if not saved:
                # Picsum direct fallback
                try:
                    picsum_url = f"https://picsum.photos/seed/{uuid.uuid4().hex[:8]}/1200/800.jpg"
                    resp = requests.get(picsum_url, timeout=15)
                    ctype = resp.headers.get('Content-Type','')
                    if verbose_images:
                        self.stdout.write(f"    Picsum fallback status={resp.status_code} ctype={ctype}")
                    if resp.status_code == 200 and ctype.startswith('image') and len(resp.content) > 1024:
                        tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                        tmp.write(resp.content)
                        tmp.flush()
                        post.image.save(f"blog_{post.slug}.jpg", File(tmp), save=True)
                        saved = True
                except Exception as e:
                    if verbose_images:
                        self.stdout.write(f"    Picsum fallback exception: {e}")
            if not saved and allow_placeholder:
                ph = generate_placeholder(post, primary_kw)
                if ph:
                    post.image.save(ph.name, ph, save=True)
                    saved = True
                    if verbose_images:
                        self.stdout.write("    Used generated placeholder image")
            if not saved and verbose_images:
                self.stdout.write(self.style.WARNING(f"    Failed image fetch for {post.slug}"))
            return saved

        if backfill_only:
            if not fetch_images:
                self.stdout.write(self.style.ERROR("--backfill-missing-images requires --fetch-images"))
                return
            imageless = (BlogPost.objects.filter(image='') | BlogPost.objects.filter(image__isnull=True)).order_by('-created_at')
            processed = 0
            success = 0
            for post in imageless[:count]:
                tags = list(post.tags.values_list('name', flat=True))
                primary_kw = tags[:2] or IMAGE_QUERY_FALLBACKS[:2]
                secondary_kw = tags[2:4]
                if fetch_and_attach_image(post, primary_kw, secondary_kw):
                    success += 1
                processed += 1
            self.stdout.write(self.style.SUCCESS(f"Backfill complete. processed={processed} images_added={success}"))
            return

        topics = list(ALL_TOPICS)
        random.shuffle(topics)
        if count < len(topics):
            topics = topics[:count]
        authors = ensure_author_pool()
        created = 0
        img_success = 0
        for (title, primary_kw, secondary_kw) in topics:
            slug = unique_slug(title)
            keywords_display = ", ".join(primary_kw[:2])
            concepts = ", ".join(secondary_kw)
            content = build_content(title, keywords_display, concepts)
            post_author = random.choice(authors)
            post = BlogPost.objects.create(title=title, slug=slug, content=content, author=post_author, published=publish)
            post.tags.set(ensure_tags(primary_kw + secondary_kw[:2]))
            if fetch_and_attach_image(post, primary_kw, secondary_kw):
                img_success += 1
            created += 1
            if created % 5 == 0 or created == count:
                self.stdout.write(f"  Created {created}/{count} (images={img_success})")
        self.stdout.write(self.style.SUCCESS(f"Done. created={created} images_saved={img_success}"))
