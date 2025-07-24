from django.core.management.base import BaseCommand
from users.models_profile import (
    LicenseType, StateBoard, TelehealthPlatform, CityCounty, ZipCode,
    PracticeAreaTag, TreatmentApproach, ClientPopulation, Language,
    ProfessionalAssociation, Insurance, MultilingualMaterial
)

class Command(BaseCommand):
    help = 'Seed lookup tables with example data.'

    def handle(self, *args, **options):
        # Example data for each lookup table
        data = {
            LicenseType: ["LCSW", "LMFT", "LPCC", "Psychologist", "MD"],
            StateBoard: ["California", "New York", "Texas", "Florida", "Illinois"],
            TelehealthPlatform: ["Zoom", "Doxy.me", "SimplePractice", "TheraNest"],
            CityCounty: ["Los Angeles", "San Francisco", "Cook County", "Miami-Dade"],
            ZipCode: ["90001", "94102", "60601", "33101"],
            PracticeAreaTag: ["Anxiety", "Depression", "Trauma", "Couples", "Teens"],
            TreatmentApproach: ["CBT", "DBT", "EMDR", "Mindfulness"],
            ClientPopulation: ["Adults", "Children", "Teens", "Seniors"],
            Language: ["English", "Spanish", "Mandarin", "French"],
            ProfessionalAssociation: ["NASW", "APA", "AAMFT", "ACA"],
            Insurance: ["Aetna", "Blue Cross", "Cigna", "United"],
            MultilingualMaterial: ["Spanish Brochure", "Mandarin Consent Form"]
        }
        for model, items in data.items():
            for value in items:
                if model.__name__ == 'ZipCode':
                    obj, created = model.objects.get_or_create(code=value)
                else:
                    obj, created = model.objects.get_or_create(name=value)
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Added {value} to {model.__name__}"))
                else:
                    self.stdout.write(f"{value} already exists in {model.__name__}")
        self.stdout.write(self.style.SUCCESS('Lookup tables seeded.'))
