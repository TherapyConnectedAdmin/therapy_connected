from django.core.management.base import BaseCommand
from users.models_profile import TherapistProfile

# City/state to zip code mapping (sample, can be expanded)
CITY_STATE_ZIP = {
    ("New York", "NY"): "10001",
    ("Los Angeles", "CA"): "90001",
    ("Chicago", "IL"): "60601",
    ("Houston", "TX"): "77001",
    ("Phoenix", "AZ"): "85001",
    ("Philadelphia", "PA"): "19101",
    ("San Antonio", "TX"): "78201",
    ("San Diego", "CA"): "92101",
    ("Dallas", "TX"): "75201",
    ("San Jose", "CA"): "95101",
}

class Command(BaseCommand):
    help = 'Update zip_code for TherapistProfiles to match their city/state.'

    def handle(self, *args, **options):
        count = 0
        for profile in TherapistProfile.objects.all():
            key = (profile.city, profile.state)
            zip_code = CITY_STATE_ZIP.get(key)
            if zip_code:
                profile.zip_code = zip_code
                profile.save()
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Updated zip_code for {count} therapist profiles to match city/state.'))
