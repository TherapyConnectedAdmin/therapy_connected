from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models_profile import TherapistProfile, LicenseType, PracticeAreaTag
import random, string
from datetime import datetime, timedelta
from faker import Faker

class Command(BaseCommand):
    help = 'Seed 100 test users and therapist profiles.'

    def handle(self, *args, **options):
        import requests
        from django.core.files.base import ContentFile
        User = get_user_model()
        fake = Faker()
        zip_codes = [f"{random.randint(10000, 99999)}" for _ in range(100)]
        license_types = list(LicenseType.objects.all())
        if not license_types:
            license_types = [
                LicenseType.objects.create(name="LCSW", description="Licensed Clinical Social Worker"),
                LicenseType.objects.create(name="LMFT", description="Licensed Marriage and Family Therapist")
            ]
        practice_tags = list(PracticeAreaTag.objects.all())
        if not practice_tags:
            practice_tags = [PracticeAreaTag.objects.create(name="Anxiety"), PracticeAreaTag.objects.create(name="Couples"), PracticeAreaTag.objects.create(name="Trauma")]
        genders = ["men", "women"]
        for i in range(100):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'is_active': True,
                    'onboarding_status': 'active',
                }
            )
            # Random last_login within last 30 days
            user.last_login = datetime.now() - timedelta(days=random.randint(0, 30))
            user.save()
            gender = random.choice(genders)
            photo_id = random.randint(1, 99)
            profile_photo_url = f"https://randomuser.me/api/portraits/{gender}/{photo_id}.jpg"
            chosen_license = random.choice(license_types)
            profile, _ = TherapistProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'credentials': chosen_license.name,
                    'display_name': f"Dr. {first_name} {last_name}",
                    'tagline': fake.sentence(nb_words=6),
                    'short_bio': fake.text(max_nb_chars=200),
                    'license_number': ''.join(random.choices(string.digits, k=8)),
                    'license_type': chosen_license,
                    'primary_office_address': fake.address(),
                    'phone_number': fake.phone_number(),
                    'email_address': email,
                    'zip_code': zip_codes[i],
                    'session_fee_package_rates': "$100/hr",
                }
            )
            # Download and upload profile photo to S3 via ImageField
            try:
                response = requests.get(profile_photo_url)
                if response.status_code == 200:
                    file_name = f"profile_{user.id}.jpg"
                    profile.profile_photo.save(file_name, ContentFile(response.content), save=True)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to upload photo for {email}: {e}"))
            # Assign random practice tags for specialties
            profile.practice_areas_tags.set(random.sample(practice_tags, k=min(2, len(practice_tags))))
            # Save credential description for card display
            profile.credential_description = chosen_license.description if hasattr(chosen_license, 'description') else ""
            profile.save()
        self.stdout.write(self.style.SUCCESS('Seeded 100 test users and therapist profiles with S3 profile photos.'))
