from django.core.management.base import BaseCommand
from users.models_profile import TherapistProfile
import random

class Command(BaseCommand):
    help = 'Populate city and state for all TherapistProfiles with random US locations.'

    def handle(self, *args, **options):
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
        states = ['NY', 'CA', 'IL', 'TX', 'AZ', 'PA', 'TX', 'CA', 'TX', 'CA']
        profiles = TherapistProfile.objects.all()
        for profile in profiles:
            idx = random.randint(0, len(cities) - 1)
            profile.city = cities[idx]
            profile.state = states[idx]
            profile.save()
        self.stdout.write(self.style.SUCCESS(f'Populated city and state for {profiles.count()} therapist profiles.'))
