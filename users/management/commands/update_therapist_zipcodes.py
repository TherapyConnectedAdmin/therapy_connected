from django.core.management.base import BaseCommand
from users.models_profile import TherapistProfile

class Command(BaseCommand):
    help = 'Update therapist zip codes to match their city/state using uszipcode.'

    def handle(self, *args, **options):
        try:
            from uszipcode import SearchEngine
        except ImportError:
            self.stdout.write(self.style.ERROR('uszipcode is not installed. Please install it first.'))
            return

        search = SearchEngine()
        updated = 0
        for therapist in TherapistProfile.objects.all():
            city = therapist.city
            state = therapist.state
            if city and state:
                results = search.by_city_and_state(city, state)
                if results:
                    zipcode = results[0].zipcode
                    if zipcode and therapist.zip_code != zipcode:
                        therapist.zip_code = zipcode
                        therapist.save()
                        updated += 1
                        self.stdout.write(f'Updated {therapist.first_name} {therapist.last_name}: {city}, {state} -> {zipcode}')
        self.stdout.write(self.style.SUCCESS(f'Zip codes updated for {updated} therapists.'))
