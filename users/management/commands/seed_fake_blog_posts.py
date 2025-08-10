from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction
from faker import Faker
from users.models_blog import BlogPost, BlogTag
import random, uuid, requests, tempfile, os
from django.core.files import File

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


def ensure_author():
    author = User.objects.filter(is_superuser=True).order_by('id').first()
    if author:
        return author
    # fallback: any existing
    any_user = User.objects.order_by('id').first()
    if any_user:
        return any_user
    # create a seed author
    email = f"editor.{uuid.uuid4().hex[:6]}@example.com"
    return User.objects.create_user(username=email, email=email, password="password123")


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

    @transaction.atomic
    def handle(self, *args, **opts):
        count = opts['count']
        purge = opts['purge']
        fetch_images = opts['fetch_images']
        publish = opts['publish']
        seed = opts.get('seed')
        if seed is not None:
            random.seed(seed); Faker.seed(seed)
        if purge:
            qs = BlogPost.objects.filter(author__email__icontains='editor.')
            deleted = qs.count()
            qs.delete()
            self.stdout.write(self.style.WARNING(f"Purged {deleted} existing seeded posts"))
        topics = list(ALL_TOPICS)
        random.shuffle(topics)
        if count < len(topics):
            topics = topics[:count]
        author = ensure_author()
        created = 0
        for idx, (title, primary_kw, secondary_kw) in enumerate(topics, start=1):
            slug = unique_slug(title)
            keywords_display = ", ".join(primary_kw[:2])
            concepts = ", ".join(secondary_kw)
            content = build_content(title, keywords_display, concepts)
            post = BlogPost.objects.create(
                title=title,
                slug=slug,
                content=content,
                author=author,
                published=publish,
            )
            # Tags: combine primary and a subset of secondary
            tag_objs = ensure_tags(primary_kw + secondary_kw[:2])
            post.tags.set(tag_objs)
            if fetch_images:
                try:
                    img_url = pick_image_url(primary_kw, secondary_kw)
                    resp = requests.get(img_url, timeout=20)
                    if resp.status_code == 200 and resp.headers.get('Content-Type','').startswith('image'):
                        tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                        tmp.write(resp.content)
                        tmp.flush()
                        post.image.save(f"blog_{slug}.jpg", File(tmp), save=True)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Image fetch failed for {slug}: {e}"))
            created += 1
            if created % 5 == 0 or created == count:
                self.stdout.write(f"  Created {created}/{count}")
        self.stdout.write(self.style.SUCCESS(f"Done. created={created}"))
