"""
Standalone script to generate fake Users and TherapistProfiles with all fields, including locations, images, and related data.
Run with: python manage.py shell < scripts/generate_fake_therapists.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapy_connected.settings')
django.setup()
import random

# List of known valid US zip codes (sampled from major cities)
VALID_US_ZIPS = [
    "10001", "90001", "60601", "77001", "85001", "19104", "33101", "98101", "30301", "80201",
    "15201", "55401", "46201", "64101", "37201", "48201", "70112", "20001", "96801", "99501", "32550"
]
def get_valid_zip():
    return random.choice(VALID_US_ZIPS)
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
    PaymentMethodSelection, TherapyTypeSelection, OtherTherapyType, AgeGroup, ParticipantType
)

fake = Faker()
User = get_user_model()

PROFILE_IMAGE_URLS = [
    "https://randomuser.me/api/portraits/men/1.jpg",
    "https://randomuser.me/api/portraits/women/2.jpg",
    "https://randomuser.me/api/portraits/men/3.jpg",
    "https://randomuser.me/api/portraits/women/4.jpg",
    "https://randomuser.me/api/portraits/men/5.jpg",
    "https://randomuser.me/api/portraits/women/6.jpg",
    "https://randomuser.me/api/portraits/men/7.jpg",
    "https://randomuser.me/api/portraits/women/8.jpg",
]
GALLERY_IMAGE_URLS = [
    "https://placekitten.com/400/300",
    "https://placebear.com/400/300",
    "https://picsum.photos/400/300",
    "https://loremflickr.com/400/300/therapy",
    "https://loremflickr.com/400/300/office",
]
VIDEO_URLS = [
    "https://samplelib.com/mp4/sample-5s.mp4",
    "https://samplelib.com/mp4/sample-10s.mp4",
    # Add more as needed
]

STATES = [
    "CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI", "AZ", "WA", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN"
]

NUM_PROFILES = 20

# Helper to get random instance from a model
get_random = lambda model: model.objects.order_by('?').first()
get_random_many = lambda model, n: random.sample(list(model.objects.all()), min(n, model.objects.count()))

def create_fake_profile():

    # Create User
    first = fake.first_name()
    last = fake.last_name()
    email = f"{first.lower()}.{last.lower()}@example.com"
    user = User.objects.create_user(username=email, email=email, password="password123")
    user.onboarding_status = 'active'
    user.is_active = True
    user.save()

    # Pick a random license type or fallback to 'Other'
    license_type = get_random(LicenseType) or LicenseType.objects.get_or_create(name='Other')[0]
    print('DEBUG: About to create TherapistProfile')
    profile = TherapistProfile(
        user=user,
        first_name=first,
        middle_name=fake.first_name() if random.random() < 0.3 else "",
        last_name=last,
        title=get_random(Title),
        display_title=random.choice([True, False]),
        personal_statement_q1=fake.paragraph(),
        personal_statement_q2=fake.paragraph(),
        personal_statement_q3=fake.paragraph(),
        practice_name=fake.company(),
        phone_number=fake.phone_number(),
        phone_extension=str(random.randint(100,999)) if random.random() < 0.5 else "",
        receive_calls_from_client=random.choice([True, False]),
        mobile_number=fake.phone_number(),
        receive_texts_from_clients=random.choice([True, False]),
        office_email=email,
        receive_emails_from_clients=random.choice([True, False]),
        receive_emails_when_client_calls=random.choice([True, False]),
        intro_statement=fake.text(max_nb_chars=200),
        therapy_delivery_method=random.choice(["In-person", "Online", "Hybrid"]),
        accepting_new_clients=random.choice(["Yes", "No", "Waitlist"]),
        offers_intro_call=random.choice([True, False]),
        individual_session_cost=str(random.randint(80, 250)),
        couples_session_cost=str(random.randint(100, 350)),
        sliding_scale_pricing_available=random.choice([True, False]),
        finance_note=fake.sentence(),
        credentials_note=fake.text(max_nb_chars=200),
        practice_website_url=fake.url(),
        facebook_url=fake.url(),
        instagram_url=fake.url(),
        linkedin_url=fake.url(),
        twitter_url=fake.url(),
        tiktok_url=fake.url(),
        youtube_url=fake.url(),
        therapy_types_note=fake.sentence(),
        specialties_note=fake.sentence(),
        mental_health_role=random.choice(["Therapist", "Psychiatrist", "Coach"]),
        license_number=fake.bothify(text='??#####'),
        license_expiration=f"{random.randint(2025,2030)}-12",
        # credential_type removed
        license_state=random.choice(STATES),
        date_of_birth=fake.date_of_birth(minimum_age=28, maximum_age=70),
        gender=get_random(Gender),
        license_type=license_type,
    )
    print('DEBUG: TherapistProfile created')
    profile.save()
    # Download a random profile image and upload to S3 (optional)
    try:
        img_url = random.choice(PROFILE_IMAGE_URLS)
        response = requests.get(img_url, timeout=10)
        if response.status_code == 200:
            tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
            tmp.write(response.content)
            tmp.flush()
            profile_photo_file = File(tmp, name=f"profile_{first.lower()}_{last.lower()}.jpg")
            profile.profile_photo.save(profile_photo_file.name, profile_photo_file, save=True)
    except Exception as e:
        pass

    # Assign random participant types and age groups (new normalized fields)
    all_participant_types = list(ParticipantType.objects.all())
    all_age_groups = list(AgeGroup.objects.all())
    if all_participant_types:
        profile.participant_types.set(random.sample(all_participant_types, random.randint(1, min(2, len(all_participant_types)))))
    if all_age_groups:
        profile.age_groups.set(random.sample(all_age_groups, random.randint(1, min(3, len(all_age_groups)))))

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
    # Specialties
    for s in get_random_many(SpecialtyLookup, random.randint(1, 5)):
        Specialty.objects.create(therapist=profile, specialty=s, is_top_specialty=random.choice([True, False]))
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
    for _ in range(random.randint(1, 3)):
        # Download and upload gallery image
        gallery_img_url = random.choice(GALLERY_IMAGE_URLS)
        gallery_file = None
        try:
            response = requests.get(gallery_img_url, timeout=10)
            if response.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.jpg')
                tmp.write(response.content)
                tmp.flush()
                gallery_file = File(tmp, name=f"gallery_{profile.pk}_{random.randint(1000,9999)}.jpg")
        except Exception as e:
            gallery_file = None
        if gallery_file:
            GalleryImage.objects.create(therapist=profile, image=gallery_file, caption=fake.sentence())
    # Video Gallery
    for _ in range(random.randint(0, 2)):
        VideoGallery.objects.create(therapist=profile, video=random.choice(VIDEO_URLS), caption=fake.sentence())
    # Locations (1-3 per profile)
    num_locations = random.randint(1, 3)
    for i in range(num_locations):
        Location.objects.create(
            therapist=profile,
            practice_name=profile.practice_name if i == 0 else fake.company(),
            street_address=fake.street_address(),
            address_line_2=fake.secondary_address(),
            city=fake.city(),
            state=random.choice(STATES),
            zip=get_valid_zip(),
            hide_address_from_public=random.choice([True, False]),
            is_primary_address=(i == 0)
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
    # Therapy Types
    for tt in get_random_many(TherapyType, random.randint(1, 4)):
        TherapyTypeSelection.objects.create(therapist=profile, therapy_type=tt)

for _ in range(NUM_PROFILES):
    create_fake_profile()

print(f"Created {NUM_PROFILES} fake therapist profiles.")
