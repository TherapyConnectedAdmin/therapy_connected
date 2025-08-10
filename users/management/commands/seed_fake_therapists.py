from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker
import random, uuid, tempfile, requests, os
from users.models_profile import (
    TherapistProfile, Title, Gender, RaceEthnicity, Faith, LGBTQIA, OtherIdentity,
    InsuranceProvider, LicenseType, PaymentMethod, TherapyType, SpecialtyLookup,
    Credential, Education, AdditionalCredential, Specialty, AreasOfExpertise,
    Location, GalleryImage, VideoGallery, ProfessionalInsurance, InsuranceDetail,
    RaceEthnicitySelection, FaithSelection, LGBTQIASelection, OtherIdentitySelection,
    PaymentMethodSelection, TherapyTypeSelection, OtherTherapyType, AgeGroup, ParticipantType, ZipCode
)
from datetime import date
from django.core.files import File

MIN_PORTRAIT_SIDE = 900  # enforce fetching images at least this large before variant processing
ADULT_MIN_AGE = 25
ADULT_PRAVATAR_IDS = [i for i in range(15, 71)]  # heuristic: skip lower ids that may include younger-looking faces

fake = Faker()
User = get_user_model()

RANDOMUSER_POOL = {('men', i) for i in range(0, 100)} | {('women', i) for i in range(0, 100)}
randomuser_used = set()

STREET_SUFFIXES = ['St', 'Ave', 'Blvd', 'Rd', 'Ln', 'Dr', 'Ct', 'Way', 'Pl']

VIDEO_URLS = [
    "https://samplelib.com/mp4/sample-5s.mp4",
    "https://samplelib.com/mp4/sample-10s.mp4",
]

MENTAL_HEALTH_ROLE_BY_CATEGORY = {
    'Psychiatry': 'Psychiatrist',
    'Psychology': 'Psychologist',
    'Social Work': 'Therapist',
    'Marriage & Family': 'Therapist',
    'Counseling': 'Therapist',
    'Behavior Analysis': 'Behavior Analyst',
    'Nursing': 'Psychiatric NP',
    'Substance Use': 'Substance Use Counselor',
}


def reserve_randomuser_portrait():
    """Return (gender_category, url) for legacy small portrait (fallback only)."""
    remaining = list(RANDOMUSER_POOL - randomuser_used)
    if not remaining:
        randomuser_used.clear()
        remaining = list(RANDOMUSER_POOL)
    gender_cat, idx = random.choice(remaining)
    randomuser_used.add((gender_cat, idx))
    url = f"https://randomuser.me/api/portraits/{gender_cat}/{idx}.jpg"
    return gender_cat, url

def portrait_url(gender_cat: str, use_hires: bool = True) -> str:
    """Return a portrait URL biased to only human faces.

    Sources (chosen via env PROFILE_PORTRAIT_SOURCE):
      synthetic (default) -> thispersondoesnotexist.com (AI generated 1024x1024 faces)
      pravatar            -> i.pravatar.cc 800px avatars
      picsum              -> (fallback) seeded picsum (may include non-people)
      randomuser          -> legacy small randomuser portraits (low-res fallback)
    """
    source = os.environ.get('PROFILE_PORTRAIT_SOURCE', 'synthetic').lower()
    if not use_hires:
        source = 'randomuser'
    if source == 'synthetic':
        # thispersondoesnotexist returns a new face each request; add cache-busting query
        return f"https://thispersondoesnotexist.com/?seed={uuid.uuid4().hex}"
    if source == 'pravatar':
        # pravatar has ~70 images; cycle randomly; gender not strictly enforced
        img_id = random.randint(1, 70)
        return f"https://i.pravatar.cc/800?img={img_id}"
    if source == 'picsum':
        seed = f"face-{gender_cat}-{uuid.uuid4().hex[:12]}"
        return f"https://picsum.photos/seed/{seed}/800/800.jpg"
    # default randomuser small (women/men categories)
    _, legacy = reserve_randomuser_portrait()
    return legacy


def generate_street_name():
    return f"{fake.last_name()} {random.choice(STREET_SUFFIXES)}"

_zip_cache = None

try:
    from scripts.real_us_addresses import ADDRESS_POOL
except Exception:
    ADDRESS_POOL = None

def generate_us_location():
    """Return a plausible US location.
    Prefers curated real addresses when FAKE_USE_REAL_ADDRESSES env var is truthy (default) for map accuracy.
    Falls back to random synthetic address within a real zip code.
    """
    use_real = os.environ.get('FAKE_USE_REAL_ADDRESSES', '1') not in ('0', 'false', 'False')
    if use_real and ADDRESS_POOL is not None:
        addr = ADDRESS_POOL.next()
        return {
            'practice_name': addr.get('practice_name', ''),
            'street_address': addr['street_address'],
            'city': addr['city'],
            'state': addr['state'],
            'zip': addr['zip'],
        }
    global _zip_cache
    if _zip_cache is None:
        _zip_cache = list(ZipCode.objects.values_list('zip', flat=True))
    if not _zip_cache:
        raise RuntimeError("ZipCode table empty. Run seed_zipcodes_full first.")
    zcode = random.choice(_zip_cache)
    zrow = ZipCode.objects.filter(pk=zcode).only('city','state','zip').first()
    street_num = random.randint(10, 9999)
    return {
        'practice_name': '',
        'street_address': f"{street_num} {generate_street_name()}",
        'city': zrow.city,
        'state': zrow.state,
        'zip': zrow.zip,
    }


def build_intro():
    adjectives = ["collaborative", "grounded", "holistic", "evidence-based", "trauma-informed", "strengths-focused"]
    focuses = ["anxiety", "life transitions", "identity development", "relationships", "burnout", "trauma recovery"]
    return ' '.join([
        f"I offer a {random.choice(adjectives)} space for meaningful change.",
        f"My work often centers around {random.choice(focuses)} and related patterns.",
        "Together we'll clarify goals, build skills, and expand resilience."
    ])


def build_therapy_note(modality_names, license_role):
    """Return a coherent paragraph describing therapeutic approach."""
    style_terms = ["collaborative", "integrative", "trauma-informed", "strengths-based", "attachment-aware", "culturally responsive"]
    verbs = ["integrate", "blend", "draw from", "synthesize"]
    focuses = ["evidence-based practices", "relational depth", "skill development", "mind-body awareness", "self-compassion"]
    chosen = ', '.join(modality_names[:4]) if modality_names else 'several evidence-based modalities'
    return (
        f"My approach is {random.choice(style_terms)} and {random.choice(style_terms)}. "
        f"I {random.choice(verbs)} {chosen} while centering {random.choice(focuses)} and pacing the work collaboratively. "
        f"As a {license_role}, I adapt interventions to each client's lived experience and goals."
    )


def build_specialties_note(specialty_names):
    if not specialty_names:
        return "I support clients navigating anxiety, identity development, and life transitions."
    primary = ', '.join(specialty_names[:4])
    return (
        f"Focus areas include {primary}. Sessions often explore how these themes intersect with relationships, work, and identity. "
        "Additional concerns are always welcome in the therapy room."
    )


def build_finance_note(individual_cost, couples_cost, sliding, insurance_names, payment_methods):
    parts = []
    parts.append(f"Standard individual sessions are ${individual_cost} and couples sessions are ${couples_cost}.")
    if sliding:
        parts.append("A limited sliding scale is available based on financial need.")
    if insurance_names:
        shown = ', '.join(insurance_names[:3])
        more = ' and more' if len(insurance_names) > 3 else ''
        parts.append(f"Currently working with {shown}{more}; I can also provide a superbill for out-of-network reimbursement.")
    else:
        parts.append("I'm an out-of-network provider; I supply detailed superbills for potential reimbursement.")
    if payment_methods:
        pm = ', '.join(payment_methods[:3])
        parts.append(f"Accepted payment methods include {pm}.")
    parts.append("Feel free to ask about affordability—accessibility matters.")
    return ' '.join(parts)


def build_ps_q1(modalities, license_type_obj):
    style_terms = ["collaborative", "integrative", "trauma-informed", "attachment-aware", "strengths-based", "client-centered"]
    core = ', '.join(modalities[:3]) if modalities else 'evidence-based methods'
    role = getattr(license_type_obj, 'short_description', '') or getattr(license_type_obj, 'name', 'Clinician')
    return (
        f"As a {role}, I use a {random.choice(style_terms)} approach, drawing from {core}. "
        f"Together we shape a pace that balances depth with steadiness, inviting curiosity and practical change."
    )[:500]


def build_ps_q2(specialties, age_groups, participant_types):
    pops = ', '.join(age_groups[:2]) if age_groups else 'diverse age groups'
    parts = ', '.join(participant_types[:2]) if participant_types else 'individuals'
    focus = ', '.join(specialties[:4]) if specialties else 'anxiety, life transitions, and identity development'
    return (
        f"I work with {pops} and {parts}. Presenting concerns often include {focus}. "
        "I aim to hold an affirming space that honors culture, identity, and systemic context."
    )[:500]


def build_ps_q3(modalities):
    process_terms = ["goal setting", "skill practice", "mind-body awareness", "reflective integration", "collaborative feedback"]
    mod = modalities[0] if modalities else 'integrative techniques'
    return (
        f"Early sessions emphasize rapport, clarity of goals, and {random.choice(process_terms)}. "
        f"As trust builds we deepen work and selectively incorporate {mod} to support sustainable change."
    )[:500]

def build_credentials_note(license_type_obj, years_experience, modalities):
    role = getattr(license_type_obj, 'short_description', '') or getattr(license_type_obj, 'name', 'Clinician')
    mod_part = ', '.join(modalities[:3]) if modalities else 'several evidence-based approaches'
    verbs = ["completed advanced training in", "pursued continuing education focused on", "regularly integrate updated research on"]
    return (
        f"{years_experience}+ years practicing as a {role}. I {random.choice(verbs)} {mod_part}. "
        "Committed to lifelong learning, supervision, and ethical, culturally attuned care."
    )


def unique_email(first, last):
    while True:
        candidate = f"{first.lower()}.{last.lower()}.{uuid.uuid4().hex[:8]}@example.com"
        if not User.objects.filter(username=candidate).exists():
            return candidate


def purge_example_therapists():
    qs = TherapistProfile.objects.filter(user__email__iendswith='@example.com')
    count = qs.count()
    user_ids = list(qs.values_list('user_id', flat=True))
    User.objects.filter(id__in=user_ids).delete()  # cascades
    return count


def create_one(index, license_types, fetch_media=True, use_hires=True, adult_only=False):
    # Phase 1: obtain gender from randomuser API (metadata only) for realism.
    inferred_gender = None
    if fetch_media:
        # Attempt to fetch gender (and age if adult_only) from randomuser API; loop until age threshold or attempts exhausted
        for _ in range(5 if adult_only else 1):
            try:
                inc_fields = 'gender,dob' if adult_only else 'gender'
                meta = requests.get(f"https://randomuser.me/api/?inc={inc_fields}&noinfo=1", timeout=10)
                if meta.status_code == 200:
                    j = meta.json(); r = j['results'][0]
                    inferred_gender = r.get('gender')
                    if adult_only:
                        dob = r.get('dob', {})
                        age_val = dob.get('age')
                        if isinstance(age_val, int) and age_val >= ADULT_MIN_AGE:
                            break
                        else:
                            inferred_gender = None  # force retry for underage
                            continue
                    break
            except Exception:
                break
    if inferred_gender not in ('male','female'):
        inferred_gender = random.choice(['male','female'])
    portrait_gender_cat = 'men' if inferred_gender == 'male' else 'women'
    # Phase 2: fetch a high-res portrait (synthetic default) independent of gender (face generator is ungendered but neutral)
    portrait_bytes = None
    if fetch_media:
        from io import BytesIO
        from PIL import Image, ImageFilter
        if adult_only:
            # Restrict to curated pravatar set for more consistently adult faces
            attempts = ['pravatar']
        else:
            attempts = [os.environ.get('PROFILE_PORTRAIT_SOURCE','synthetic').lower(), 'synthetic', 'pravatar']
        seen = set(); ordered = []
        for a in attempts:
            if a not in seen:
                ordered.append(a); seen.add(a)
        for src in ordered:
            try:
                resp = None; hdrs = {}
                if src == 'synthetic':
                    url = f"https://thispersondoesnotexist.com/?seed={uuid.uuid4().hex}"
                    hdrs['User-Agent'] = 'Mozilla/5.0 (compatible; TCSeedBot/1.0)'
                    resp = requests.get(url, timeout=20, headers=hdrs)
                elif src == 'pravatar':
                    if adult_only:
                        img_id = random.choice(ADULT_PRAVATAR_IDS)
                    else:
                        img_id = random.randint(1, 70)
                    url = f"https://i.pravatar.cc/1200?img={img_id}"
                    resp = requests.get(url, timeout=15)
                elif src == 'randomuser_api':  # fallback only if explicitly requested
                    g_req = inferred_gender
                    r2 = requests.get(f"https://randomuser.me/api/?gender={g_req}&inc=picture&noinfo=1", timeout=10)
                    if r2.status_code == 200:
                        j = r2.json(); url = j['results'][0]['picture']['large']; resp = requests.get(url, timeout=10)
                else:
                    continue
                if not resp or resp.status_code != 200 or not resp.headers.get('Content-Type','').startswith('image'):
                    continue
                raw = resp.content
                try:
                    img = Image.open(BytesIO(raw))
                    w, h = img.size
                except Exception:
                    continue
                if max(w, h) < 900 and src != 'randomuser_api':
                    # reject low native resolution from non-primary sources
                    continue
                # Normalize/upscale (rare) to at least 1200 on long side for consistency
                try:
                    img = img.convert('RGB')
                    if max(w, h) < 1200:
                        scale = 1200.0 / float(max(w, h))
                        img = img.resize((int(w*scale), int(h*scale)), Image.Resampling.LANCZOS)
                    img = img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))
                    buf = BytesIO(); img.save(buf, format='JPEG', quality=90, optimize=True, progressive=True); portrait_bytes = buf.getvalue()
                except Exception:
                    portrait_bytes = raw
                if portrait_bytes:
                    break
            except Exception:
                continue
    first = fake.first_name_male() if portrait_gender_cat == 'men' else fake.first_name_female()
    gender_lookup_name = 'Male' if portrait_gender_cat == 'men' else 'Female'
    last = fake.last_name()
    email = unique_email(first, last)
    user = User.objects.create_user(username=email, email=email, password='password123', is_active=True)
    user.onboarding_status = 'active'
    user.save()

    license_type = license_types[index % len(license_types)]
    chosen_modalities = random.sample(list(TherapyType.objects.all()), min(random.randint(2,5), TherapyType.objects.count()))
    chosen_specialties = random.sample(list(SpecialtyLookup.objects.all()), min(random.randint(2,5), SpecialtyLookup.objects.count()))
    participant_types = list(ParticipantType.objects.all())
    chosen_participant_types = random.sample(participant_types, min(len(participant_types), random.randint(1,2))) if participant_types else []
    age_groups = list(AgeGroup.objects.all())
    chosen_age_groups = random.sample(age_groups, min(len(age_groups), random.randint(1,3))) if age_groups else []

    modalities_names = ', '.join(t.name for t in chosen_modalities[:4])
    specialties_names = ', '.join(s.name for s in chosen_specialties[:4])

    # Pre-sample insurance providers & payment methods to keep narrative consistent
    available_insurance = list(InsuranceProvider.objects.all())
    sampled_insurance = random.sample(available_insurance, min(random.randint(1,3), len(available_insurance))) if available_insurance else []
    available_payment = list(PaymentMethod.objects.all())
    sampled_payments = random.sample(available_payment, min(random.randint(1,3), len(available_payment))) if available_payment else []

    individual_cost = random.randint(80, 250)
    couples_cost = random.randint(100, 350)
    sliding = random.choice([True, False])

    years_experience = random.randint(3,25)
    therapy_types_note_text = build_therapy_note([t.name for t in chosen_modalities], getattr(license_type, 'short_description', '') or getattr(license_type, 'name', 'Clinician'))
    specialties_note_text = build_specialties_note([s.name for s in chosen_specialties])
    finance_note_text = build_finance_note(individual_cost, couples_cost, sliding, [p.name for p in sampled_insurance], [pm.name for pm in sampled_payments])
    credentials_note_text = build_credentials_note(license_type, years_experience, [t.name for t in chosen_modalities])

    profile = TherapistProfile.objects.create(
        user=user,
        first_name=first,
        last_name=last,
        title=Title.objects.order_by('?').first(),
        display_title=random.choice([True, False]),
        personal_statement_q1=build_ps_q1([t.name for t in chosen_modalities], license_type),
        personal_statement_q2=build_ps_q2([s.name for s in chosen_specialties], [a.name for a in chosen_age_groups], [p.name for p in chosen_participant_types]),
        personal_statement_q3=build_ps_q3([t.name for t in chosen_modalities]),
        practice_name=fake.company(),
        phone_number=fake.phone_number(),
        mobile_number=fake.phone_number(),
        intro_statement=build_intro(),
        therapy_delivery_method=random.choice(["In-person", "Online", "Hybrid"]),
        accepting_new_clients=random.choice(["Yes", "No", "Waitlist"]),
        offers_intro_call=random.choice([True, False]),
        individual_session_cost=str(individual_cost),
        couples_session_cost=str(couples_cost),
        sliding_scale_pricing_available=sliding,
        finance_note=finance_note_text,
        credentials_note=credentials_note_text,
        practice_website_url=fake.url(),
        therapy_types_note=therapy_types_note_text,
        specialties_note=specialties_note_text,
        mental_health_role=MENTAL_HEALTH_ROLE_BY_CATEGORY.get(getattr(license_type, 'category', ''), random.choice(["Therapist", "Clinician"])),
        license_type=license_type,
        license_number=fake.bothify(text='??#####'),
        license_expiration=f"{random.randint(2025,2030)}-12",
        license_state=fake.state_abbr(),
        date_of_birth=fake.date_of_birth(minimum_age=28, maximum_age=70),
        gender=Gender.objects.filter(name__iexact=gender_lookup_name).first() or Gender.objects.order_by('?').first(),
    )

    # Save portrait if we fetched one earlier
    if fetch_media and portrait_bytes:
        tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
        tmp.write(portrait_bytes)
        tmp.flush()
        profile.profile_photo.save(f"profile_{profile.pk}.jpg", File(tmp), save=True)

    # M2M / related creations
    if chosen_participant_types:
        profile.participant_types.set(chosen_participant_types)
    if chosen_age_groups:
        profile.age_groups.set(chosen_age_groups)

    for _ in range(random.randint(1,3)):
        Credential.objects.create(therapist=profile, license_type=license_type)
    for _ in range(random.randint(1,2)):
        Education.objects.create(therapist=profile, school=fake.company(), degree_diploma=random.choice(["PhD","MA","MSW","PsyD","MD"]), year_graduated=str(random.randint(1980,2022)))
    for _ in range(random.randint(0,2)):
        AdditionalCredential.objects.create(therapist=profile, organization_name=fake.company(), id_number=fake.bothify(text='ID####'), year_issued=str(random.randint(1980,2022)))
    for s in chosen_specialties:
        Specialty.objects.create(therapist=profile, specialty=s, is_top_specialty=random.random()<0.4)
    for _ in range(random.randint(1,3)):
        AreasOfExpertise.objects.create(therapist=profile, expertise=fake.word())
    for _ in range(random.randint(0,2)):
        OtherTherapyType.objects.create(therapist=profile, therapy_type=fake.word())
    for _ in range(random.randint(0,2)):
        from users.models_profile import OtherTreatmentOption
        OtherTreatmentOption.objects.create(therapist=profile, option_text=fake.word())
    # Gallery images
    if fetch_media:
        for _ in range(random.randint(1,3)):
            try:
                g_url = f"https://picsum.photos/seed/{uuid.uuid4().hex[:10]}/400/300"
                r2 = requests.get(g_url, timeout=10)
                if r2.status_code == 200 and r2.headers.get('Content-Type','').startswith('image'):
                    tmp2 = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                    tmp2.write(r2.content)
                    tmp2.flush()
                    GalleryImage.objects.create(therapist=profile, image=File(tmp2, name=f"gallery_{profile.pk}_{uuid.uuid4().hex[:6]}.jpg"), caption=fake.sentence())
            except Exception:
                pass
    for _ in range(random.randint(0,2)):
        VideoGallery.objects.create(therapist=profile, video=random.choice(VIDEO_URLS), caption=fake.sentence())
    # Locations
    for i in range(random.randint(1,3)):
        loc = generate_us_location()
        Location.objects.create(
            therapist=profile,
            practice_name=loc.get('practice_name') or (profile.practice_name if i == 0 else fake.company()),
            street_address=loc['street_address'],
            address_line_2=fake.secondary_address(),
            city=loc['city'], state=loc['state'], zip=loc['zip'],
            hide_address_from_public=random.choice([True, False]),
            is_primary_address=(i == 0)
        )
    for provider in sampled_insurance:
        InsuranceDetail.objects.create(therapist=profile, provider=provider, out_of_network=random.choice([True, False]))
    if random.random() < 0.7:
        ProfessionalInsurance.objects.create(therapist=profile, npi_number=fake.bothify(text='##########'), malpractice_carrier=fake.company(), malpractice_expiration_date=f"{random.randint(2025,2030)}-12")
    for race in random.sample(list(RaceEthnicity.objects.all()), min(random.randint(1,2), RaceEthnicity.objects.count())):
        RaceEthnicitySelection.objects.create(therapist=profile, race_ethnicity=race)
    for faith in random.sample(list(Faith.objects.all()), min(random.randint(0,2), Faith.objects.count())):
        FaithSelection.objects.create(therapist=profile, faith=faith)
    for lgbtq in random.sample(list(LGBTQIA.objects.all()), min(random.randint(0,2), LGBTQIA.objects.count())):
        LGBTQIASelection.objects.create(therapist=profile, lgbtqia=lgbtq)
    for other in random.sample(list(OtherIdentity.objects.all()), min(random.randint(0,2), OtherIdentity.objects.count())):
        OtherIdentitySelection.objects.create(therapist=profile, other_identity=other)
    for pm in sampled_payments:
        PaymentMethodSelection.objects.create(therapist=profile, payment_method=pm)
    for tt in chosen_modalities:
        TherapyTypeSelection.objects.create(therapist=profile, therapy_type=tt)

    return profile


class Command(BaseCommand):
    help = "Seed fake therapist profiles with realistic related data."

    def add_arguments(self, parser):
            parser.add_argument('--count', type=int, default=25, help='Number of therapists to create')
            parser.add_argument('--purge', action='store_true', help='Purge existing example.com therapist users first')
            parser.add_argument('--fetch-media', action='store_true', default=False, help='Download remote images/video thumbnails')
            parser.add_argument('--seed', type=int, help='Random seed for reproducibility')
            parser.add_argument('--no-hires', action='store_true', help='Disable high-resolution portrait source (fallback to small randomuser images)')
            parser.add_argument('--portrait-source', type=str, help='Override env PROFILE_PORTRAIT_SOURCE (synthetic|pravatar|picsum|randomuser)')
            parser.add_argument('--adult-only', action='store_true', help='Restrict portraits to adult-looking sources (pravatar curated IDs)')

    @transaction.atomic
    def handle(self, *args, **options):
        count = options['count']
        purge = options['purge']
        fetch_media = options['fetch_media']
        seed = options.get('seed')
        use_hires = not options.get('no_hires')
        override_source = options.get('portrait_source')
        adult_only = options.get('adult_only')
        if override_source:
            os.environ['PROFILE_PORTRAIT_SOURCE'] = override_source
        if seed is not None:
            random.seed(seed)
            Faker.seed(seed)
        if purge:
            deleted = purge_example_therapists()
            self.stdout.write(self.style.WARNING(f"Purged {deleted} existing example.com therapists"))

        license_types = list(LicenseType.objects.all())
        if not license_types:
            lt, _ = LicenseType.objects.get_or_create(name='Other', defaults={'short_description': 'Other'})
            license_types = [lt]
        self.stdout.write(
            f"Seeding {count} therapists (media={'on' if fetch_media else 'off'}, "
            f"hires={'on' if use_hires else 'off'}, source={os.environ.get('PROFILE_PORTRAIT_SOURCE','synthetic')})..."
        )
        for i in range(count):
            profile = create_one(i, license_types, fetch_media=fetch_media, use_hires=use_hires, adult_only=adult_only)
            if (i+1) % 10 == 0 or (i+1) == count:
                self.stdout.write(f"  Created {i+1}/{count} (id={profile.id})")
        self.stdout.write(self.style.SUCCESS("Done seeding therapists."))
