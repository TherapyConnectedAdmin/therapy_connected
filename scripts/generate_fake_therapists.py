"""
Standalone script to generate fake Users and TherapistProfiles with all fields, including locations, images, and related data.
Run with: python manage.py shell < scripts/generate_fake_therapists.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapy_connected.settings')
django.setup()
import random
from typing import List, Dict, Tuple
import uuid

#############################################
# ZipCode table integration (uses fully seeded ZipCode model)
#############################################
from users.models_profile import ZipCode
_ZIP_PK_CACHE = None

_STREET_SUFFIXES = [
    'St', 'Ave', 'Blvd', 'Rd', 'Ln', 'Dr', 'Ct', 'Way', 'Pl'
]

def _generate_street_name() -> str:
    base = fake.last_name()
    suffix = random.choice(_STREET_SUFFIXES)
    return f"{base} {suffix}"

def generate_us_location() -> Dict[str, str]:
    """Generate a US address selecting a random ZipCode row for real city/state/zip."""
    global _ZIP_PK_CACHE
    if _ZIP_PK_CACHE is None:
        _ZIP_PK_CACHE = list(ZipCode.objects.values_list('zip', flat=True))
    if not _ZIP_PK_CACHE:
        raise RuntimeError("ZipCode table empty. Run seed_zipcodes_full first.")
    zcode = random.choice(_ZIP_PK_CACHE)
    zrow = ZipCode.objects.filter(pk=zcode).only('city','state','zip').first()
    street_num = random.randint(10, 9999)
    street = _generate_street_name()
    return {
        'practice_name': '',
        'street_address': f"{street_num} {street}",
        'city': zrow.city,
        'state': zrow.state,
        'zip': zrow.zip,
    }
import tempfile
import requests
from faker import Faker
from django.core.files import File
from django.contrib.auth import get_user_model
from users.models_profile import (
    TherapistProfile, Title, Gender, RaceEthnicity, Faith, LGBTQIA, OtherIdentity,
    InsuranceProvider, LicenseType, PaymentMethod, TherapyType, SpecialtyLookup,
    Credential, Education, AdditionalCredential, Specialty, AreasOfExpertise,
    Location, GalleryImage, VideoGallery, ProfessionalInsurance, InsuranceDetail,
    RaceEthnicitySelection, FaithSelection, LGBTQIASelection, OtherIdentitySelection,
    PaymentMethodSelection, TherapyTypeSelection, OtherTherapyType, AgeGroup, ParticipantType,
    OfficeHour
)

fake = Faker()
User = get_user_model()

#############################################
# Human profile photo sourcing (randomuser.me)
#############################################
_RANDOMUSER_POOL = {('men', i) for i in range(0, 100)} | {('women', i) for i in range(0, 100)}
_RANDOMUSER_USED = set()
FAKE_HIGH_RES = os.environ.get('FAKE_HIGH_RES') == '1'

def reserve_randomuser_portrait() -> tuple[str, str]:
    """Return (gender_category, image_url) selecting either standard randomuser (128x128)
    or high-res placeholder (Picsum 600x600) when FAKE_HIGH_RES=1.
    """
    if FAKE_HIGH_RES:
        # Keep gender category for name alignment, but source a higher-res neutral image
        gender_cat = random.choice(['men', 'women'])
        # Seeded picsum for uniqueness
        seed = uuid.uuid4().hex[:16]
        url = f"https://picsum.photos/seed/{seed}/600/600.jpg"
        return gender_cat, url
    remaining = list(_RANDOMUSER_POOL - _RANDOMUSER_USED)
    if not remaining:
        _RANDOMUSER_USED.clear()
        remaining = list(_RANDOMUSER_POOL)
    gender_cat, idx = random.choice(remaining)
    _RANDOMUSER_USED.add((gender_cat, idx))
    url = f"https://randomuser.me/api/portraits/{gender_cat}/{idx}.jpg"
    return gender_cat, url
def generate_gallery_image_url() -> str:
    # picsum with unique seed for variety
    return f"https://picsum.photos/seed/{uuid.uuid4().hex[:12]}/400/300"
VIDEO_URLS = [
    "https://samplelib.com/mp4/sample-5s.mp4",
    "https://samplelib.com/mp4/sample-10s.mp4",
    # Add more as needed
]

STATES = [fake.state_abbr() for _ in range(30)]  # ephemeral pool; license_state uses this

NUM_PROFILES = int(os.environ.get('FAKE_NUM_PROFILES', '25'))
FAKE_FETCH_MEDIA = bool(int(os.environ.get('FAKE_FETCH_MEDIA', '1')))  # allow disabling network
FAKE_RANDOM_SEED = os.environ.get('FAKE_RANDOM_SEED')
if FAKE_RANDOM_SEED:
    random.seed(FAKE_RANDOM_SEED)
    Faker.seed(int(FAKE_RANDOM_SEED))

# Optional purge logic
FAKE_CLEAR_ALL = os.environ.get('FAKE_CLEAR_THERAPISTS') == '1'
FAKE_CLEAR_FAKE_ONLY = os.environ.get('FAKE_CLEAR_FAKE_ONLY') == '1'
if FAKE_CLEAR_ALL and FAKE_CLEAR_FAKE_ONLY:
    print('WARNING: Both FAKE_CLEAR_THERAPISTS and FAKE_CLEAR_FAKE_ONLY set; defaulting to clear all.')
if FAKE_CLEAR_ALL or FAKE_CLEAR_FAKE_ONLY:
    from django.db import transaction
    with transaction.atomic():
        qs = TherapistProfile.objects.all()
        if not FAKE_CLEAR_ALL:  # fake-only mode
            # Heuristic: generated users have email domain example.com per script
            qs = qs.filter(user__email__iendswith='@example.com')
        count = qs.count()
        print(f'Purging {count} therapist profiles (FAKE_CLEAR_{"ALL" if FAKE_CLEAR_ALL else "FAKE_ONLY"})...')
        # Collect user ids to delete afterwards (cascade may not delete auth user depending on FK; here user is FK in profile so deleting user cascades profile or vice versa?)
        user_ids = list(qs.values_list('user_id', flat=True))
        # Delete users directly to ensure full cascade of related objects (profile has OneToOne field to user so deleting user removes profile)
        from django.contrib.auth import get_user_model
        get_user_model().objects.filter(id__in=user_ids).delete()
        print('Purge complete.')

# Pre-fetch license types for round-robin assignment to maximize coverage
_LICENSE_TYPES = list(LicenseType.objects.order_by('name'))
random.shuffle(_LICENSE_TYPES)
if not _LICENSE_TYPES:
    # Ensure at least one placeholder
    _placeholder, _ = LicenseType.objects.get_or_create(name='Other', defaults={'short_description': 'Other'})
    _LICENSE_TYPES = [_placeholder]

# Narrative template helpers
def build_intro() -> str:
    adjectives = ["collaborative", "grounded", "holistic", "evidence-based", "trauma-informed", "strengths-focused"]
    focuses = ["anxiety", "life transitions", "identity development", "relationships", "burnout", "trauma recovery"]
    parts = [
        f"I offer a {random.choice(adjectives)} space for meaningful change.",
        f"My work often centers around {random.choice(focuses)} and related patterns.",
        f"Together we'll clarify goals, build skills, and expand resilience."
    ]
    return ' '.join(parts)

def build_therapy_note(modalities: str) -> str:
    verbs = ["integrate", "blend", "draw from", "tailor"]
    return f"I {random.choice(verbs)} {modalities} with culturally responsive, client-led pacing."

def build_specialties_note(specialties: str) -> str:
    return f"Focus areas include {specialties.lower()} among others."

def build_finance_note() -> str:
    clauses = [
        "Limited sliding scale openings available.",
        "Superbills offered for out-of-network reimbursement.",
        "Ask about reduced rates for students or early career professionals.",
    ]
    return random.choice(clauses)

#############################################
# Personal Statement Generators (distinct prompts)
#############################################
def build_ps_q1(modalities: List[str], license_type_obj) -> str:
    """Therapeutic Approach: emphasize style + core modalities."""
    style_terms = ["collaborative", "integrative", "trauma-informed", "attachment-aware", "strengths-based", "client-centered"]
    core = ', '.join(modalities[:3]) if modalities else 'evidence-based methods'
    role = getattr(license_type_obj, 'short_description', '') or getattr(license_type_obj, 'name', 'Clinician')
    return f"As a {role}, I use a {random.choice(style_terms)} approach, drawing from {core} while tailoring pace and depth to each client."[:500]

def build_ps_q2(specialties: List[str], age_groups: List[str], participant_types: List[str]) -> str:
    """Populations & Focus Areas."""
    pops = ', '.join(age_groups[:2]) if age_groups else 'diverse age groups'
    parts = ', '.join(participant_types[:2]) if participant_types else 'individuals'
    focus = ', '.join(specialties[:4]) if specialties else 'anxiety, life transitions, and identity development'
    return f"I work with {pops} and {parts}, with focus areas including {focus}. Cultural humility and inclusivity guide our work."[:500]

def build_ps_q3(modalities: List[str]) -> str:
    """What to Expect / Process."""
    process_terms = ["goal setting", "skill practice", "mind-body awareness", "routine reflection", "collaborative feedback"]
    mod = modalities[0] if modalities else 'integrative techniques'
    return f"Early sessions emphasize rapport, clarity of goals, and {random.choice(process_terms)}; over time we incorporate {mod} for sustained change."[:500]

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

# Helper to get random instance from a model
get_random = lambda model: model.objects.order_by('?').first()
get_random_many = lambda model, n: random.sample(list(model.objects.all()), min(n, model.objects.count()))

def create_fake_profile(index: int):
    # Conditional debug logging (suppress spam for large batches)
    if NUM_PROFILES <= 100 or index % 50 == 0:
        print('DEBUG: About to create TherapistProfile', index + 1, 'of', NUM_PROFILES)

    # Create User & reserve portrait for gender-aligned naming
    portrait_gender_cat, portrait_url = reserve_randomuser_portrait()
    if portrait_gender_cat == 'men':
        first = fake.first_name_male()
        gender_lookup_name = 'Male'
    else:
        first = fake.first_name_female()
        gender_lookup_name = 'Female'
    last = fake.last_name()

    def _unique_email(base_first: str, base_last: str) -> str:
        # Loop until a unique email/username is found (fast with UUID segment)
        while True:
            candidate = f"{base_first.lower()}.{base_last.lower()}.{uuid.uuid4().hex[:8]}@example.com"
            if not User.objects.filter(username=candidate).exists():
                return candidate

    email = _unique_email(first, last)
    user = User.objects.create_user(username=email, email=email, password="password123")
    user.onboarding_status = 'active'
    user.is_active = True
    user.save()

    # Round-robin license types for coverage
    license_type = _LICENSE_TYPES[index % len(_LICENSE_TYPES)]
    # (legacy debug removed; consolidated above)
    chosen_modalities = get_random_many(TherapyType, random.randint(2, 5))
    chosen_specialties = get_random_many(SpecialtyLookup, random.randint(2, 5))
    # Preselect participant types & age groups for narrative consistency
    chosen_participant_types = get_random_many(ParticipantType, random.randint(1, min(2, ParticipantType.objects.count()))) if ParticipantType.objects.exists() else []
    chosen_age_groups = get_random_many(AgeGroup, random.randint(1, min(3, AgeGroup.objects.count()))) if AgeGroup.objects.exists() else []
    modalities_names = ', '.join(t.name for t in chosen_modalities[:4])
    specialties_names = ', '.join(s.name for s in chosen_specialties[:4])
    therapy_note_tpl = build_therapy_note(modalities_names)
    specialties_note_tpl = build_specialties_note(specialties_names)
    intro_statement = build_intro()
    finance_note_text = build_finance_note()
    # Personal statement question themed content
    ps_q1 = build_ps_q1([t.name for t in chosen_modalities], license_type)
    ps_q2 = build_ps_q2([s.name for s in chosen_specialties], [a.name for a in chosen_age_groups], [p.name for p in chosen_participant_types])
    ps_q3 = build_ps_q3([t.name for t in chosen_modalities])

    # Derive mental health role from license category when available
    role = MENTAL_HEALTH_ROLE_BY_CATEGORY.get(getattr(license_type, 'category', ''), random.choice(["Therapist", "Clinician"]))

    # Attempt to set Gender model consistent with chosen name/photo if matching entries exist
    chosen_gender_obj = Gender.objects.filter(name__iexact=gender_lookup_name).first() or get_random(Gender)

    profile = TherapistProfile(
        user=user,
        first_name=first,
        middle_name=fake.first_name() if random.random() < 0.3 else "",
        last_name=last,
        title=get_random(Title),
        display_title=random.choice([True, False]),
        personal_statement_q1=ps_q1,
        personal_statement_q2=ps_q2,
        personal_statement_q3=ps_q3,
        practice_name=fake.company(),
        phone_number=fake.phone_number(),
        phone_extension=str(random.randint(100,999)) if random.random() < 0.5 else "",
        receive_calls_from_client=random.choice([True, False]),
        mobile_number=fake.phone_number(),
        receive_texts_from_clients=random.choice([True, False]),
        office_email=email,
        receive_emails_from_clients=random.choice([True, False]),
        receive_emails_when_client_calls=random.choice([True, False]),
        intro_statement=intro_statement,
        therapy_delivery_method=random.choice(["In-person", "Online", "Hybrid"]),
        accepting_new_clients=random.choice(["Yes", "No", "Waitlist"]),
        offers_intro_call=random.choice([True, False]),
        individual_session_cost=str(random.randint(80, 250)),
        couples_session_cost=str(random.randint(100, 350)),
        sliding_scale_pricing_available=random.choice([True, False]),
        finance_note=finance_note_text,
        credentials_note=fake.text(max_nb_chars=200),
        practice_website_url=fake.url(),
        facebook_url=fake.url(),
        instagram_url=fake.url(),
        linkedin_url=fake.url(),
        twitter_url=fake.url(),
        tiktok_url=fake.url(),
        youtube_url=fake.url(),
        therapy_types_note=therapy_note_tpl,
        specialties_note=specialties_note_tpl,
        mental_health_role=role,
        license_number=fake.bothify(text='??#####'),
        license_expiration=f"{random.randint(2025,2030)}-12",
        license_state=random.choice(STATES),
        date_of_birth=fake.date_of_birth(minimum_age=28, maximum_age=70),
        gender=chosen_gender_obj,
        license_type=license_type,
    )
    profile.save()
    if NUM_PROFILES <= 100 or index % 50 == 0:
        print('DEBUG: TherapistProfile created (id=', profile.id, ')')
    # Download a random profile image and upload to S3 (optional)
    if FAKE_FETCH_MEDIA:
        for attempt in range(3):
            try:
                response = requests.get(portrait_url, timeout=10)
                if response.status_code == 200 and response.headers.get('Content-Type','').startswith('image'):
                    tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                    tmp.write(response.content)
                    tmp.flush()
                    profile_photo_file = File(tmp, name=f"profile_{profile.pk}.jpg")
                    profile.profile_photo.save(profile_photo_file.name, profile_photo_file, save=True)
                    break
            except Exception:
                continue

    # Assign random participant types and age groups (new normalized fields)
    all_participant_types = list(ParticipantType.objects.all())
    all_age_groups = list(AgeGroup.objects.all())
    if chosen_participant_types:
        profile.participant_types.set(chosen_participant_types)
    if chosen_age_groups:
        profile.age_groups.set(chosen_age_groups)

    # Related fields
    for _ in range(random.randint(1, 3)):
        cred_license_type = get_random(LicenseType) or license_type
        Credential.objects.create(therapist=profile, license_type=cred_license_type)
    for _ in range(random.randint(1, 2)):
        Education.objects.create(
            therapist=profile,
            school=fake.company(),
            degree_diploma=random.choice(["PhD", "MA", "MSW", "PsyD", "MD"]),
            year_graduated=str(random.randint(1980, 2022)),
            year_began_practice=str(random.randint(1980, 2022)) if random.random() < 0.5 else ""
        )
    for _ in range(random.randint(0, 2)):
        AdditionalCredential.objects.create(
            therapist=profile,
            # credential_type removed
            organization_name=fake.company(),
            id_number=fake.bothify(text='ID####'),
            year_issued=str(random.randint(1980, 2022))
        )
    # Specialties (use chosen list for consistency with narrative)
    for s in chosen_specialties:
        Specialty.objects.create(therapist=profile, specialty=s, is_top_specialty=random.random() < 0.4)
    # Areas of Expertise
    for _ in range(random.randint(1, 3)):
        AreasOfExpertise.objects.create(therapist=profile, expertise=fake.word())
    # Other Therapy Types
    for _ in range(random.randint(0, 2)):
        OtherTherapyType.objects.create(therapist=profile, therapy_type=fake.word())
    # Other Treatment Options
    for _ in range(random.randint(0, 2)):
        from users.models_profile import OtherTreatmentOption
        OtherTreatmentOption.objects.create(therapist=profile, option_text=fake.word())
    # Gallery Images
    if FAKE_FETCH_MEDIA:
        for _ in range(random.randint(1, 3)):
            gallery_file = None
            try:
                gallery_img_url = generate_gallery_image_url()
                response = requests.get(gallery_img_url, timeout=10)
                if response.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                    tmp.write(response.content)
                    tmp.flush()
                    gallery_file = File(tmp, name=f"gallery_{profile.pk}_{random.randint(1000,9999)}.jpg")
            except Exception:
                gallery_file = None
            if gallery_file:
                GalleryImage.objects.create(therapist=profile, image=gallery_file, caption=fake.sentence())
    # Video Gallery
    for _ in range(random.randint(0, 2)):
        VideoGallery.objects.create(therapist=profile, video=random.choice(VIDEO_URLS), caption=fake.sentence())
    # Locations (1-3 per profile)
    num_locations = random.randint(1, 3)
    for i in range(num_locations):
        loc = generate_us_location()
        loc_obj = Location.objects.create(
            therapist=profile,
            practice_name=loc.get('practice_name') or (profile.practice_name if i == 0 else fake.company()),
            street_address=loc.get('street_address') or fake.street_address(),
            address_line_2=fake.secondary_address(),
            city=loc['city'],
            state=loc['state'],
            zip=loc['zip'],
            hide_address_from_public=random.choice([True, False]),
            is_primary_address=(i == 0)
        )
        # Office Hours: Mon-Fri standard block with slight randomization, weekends maybe closed or shorter
        for wd in range(7):  # 0=Mon .. 6=Sun
            # Decide closed / by appointment
            if wd >= 5:  # Sat/Sun
                if random.random() < 0.5:
                    OfficeHour.objects.create(location=loc_obj, weekday=wd, is_closed=True)
                    continue
                if random.random() < 0.3:
                    OfficeHour.objects.create(location=loc_obj, weekday=wd, by_appointment_only=True)
                    continue
                # Shorter hours weekend
                start1 = f"{random.choice(['09','10'])}:00"
                end1 = f"{random.choice(['12','13'])}:00"
                OfficeHour.objects.create(location=loc_obj, weekday=wd, start_time_1=start1, end_time_1=end1)
            else:
                # Weekday
                if random.random() < 0.05:
                    # Rare fully closed weekday (e.g., admin day)
                    OfficeHour.objects.create(location=loc_obj, weekday=wd, is_closed=True)
                    continue
                if random.random() < 0.08:
                    OfficeHour.objects.create(location=loc_obj, weekday=wd, by_appointment_only=True)
                    continue
                start_hour = random.choice(['08','09'])
                end_hour = random.choice(['16','17','18'])
                # Optional split shift (e.g., lunch break) with afternoon block
                if random.random() < 0.25:
                    OfficeHour.objects.create(
                        location=loc_obj,
                        weekday=wd,
                        start_time_1=start_hour+':00',
                        end_time_1='12:00',
                        start_time_2='13:00',
                        end_time_2=end_hour+':00',
                        notes='Lunch 12-1'
                    )
                else:
                    OfficeHour.objects.create(
                        location=loc_obj,
                        weekday=wd,
                        start_time_1=start_hour+':00',
                        end_time_1=end_hour+':00'
                    )
    # Insurance Details
    for provider in get_random_many(InsuranceProvider, random.randint(1, 3)):
        InsuranceDetail.objects.create(therapist=profile, provider=provider, out_of_network=random.choice([True, False]))
    # Professional Insurance
    if random.random() < 0.7:
        ProfessionalInsurance.objects.create(
            therapist=profile,
            npi_number=fake.bothify(text='##########'),
            malpractice_carrier=fake.company(),
            malpractice_expiration_date=f"{random.randint(2025,2030)}-12"
        )
    # Selections for identity fields
    for race in get_random_many(RaceEthnicity, random.randint(1, 2)):
        RaceEthnicitySelection.objects.create(therapist=profile, race_ethnicity=race)
    for faith in get_random_many(Faith, random.randint(0, 2)):
        FaithSelection.objects.create(therapist=profile, faith=faith)
    for lgbtq in get_random_many(LGBTQIA, random.randint(0, 2)):
        LGBTQIASelection.objects.create(therapist=profile, lgbtqia=lgbtq)
    for other in get_random_many(OtherIdentity, random.randint(0, 2)):
        OtherIdentitySelection.objects.create(therapist=profile, other_identity=other)
    # Payment Methods
    for pm in get_random_many(PaymentMethod, random.randint(1, 3)):
        PaymentMethodSelection.objects.create(therapist=profile, payment_method=pm)
    # Therapy Types (use narrative set)
    for tt in chosen_modalities:
        TherapyTypeSelection.objects.create(therapist=profile, therapy_type=tt)

for i in range(NUM_PROFILES):
    create_fake_profile(i)

print(f"Created {NUM_PROFILES} fake therapist profiles.")
