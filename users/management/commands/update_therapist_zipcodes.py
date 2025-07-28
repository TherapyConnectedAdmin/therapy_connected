from django.core.management.base import BaseCommand
from users.models_profile import TherapistProfile

class Command(BaseCommand):
    help = 'Update therapist zip codes to match their city/state using uszipcode.'

    def handle(self, *args, **options):
        try:
            from faker import Faker
        except ImportError:
            self.stdout.write(self.style.ERROR('Faker is not installed. Please install it first.'))
            return

        fake = Faker()
        updated = 0
        for therapist in TherapistProfile.objects.all():
            city = fake.city()
            state = fake.state_abbr()
            zipcode = fake.zipcode_in_state(state)
            therapist.city = city
            therapist.state = state
            therapist.zip_code = zipcode
            therapist.save()
            updated += 1
            self.stdout.write(f'Updated {therapist.first_name} {therapist.last_name}: {city}, {state} -> {zipcode}')
        self.stdout.write(self.style.SUCCESS(f'Random city, state, and zip codes assigned for {updated} therapists.'))
