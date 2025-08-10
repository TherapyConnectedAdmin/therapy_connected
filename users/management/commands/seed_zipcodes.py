from django.core.management.base import BaseCommand
from users.models_profile import ZipCode
import csv, os, sys

DEFAULT_SOURCE = os.environ.get('ZIPCODE_SOURCE_CSV', 'scripts/data/us_zip_public.csv')

class Command(BaseCommand):
    help = 'Seed ZipCode table from CSV (zip,city,state,latitude,longitude). Skips existing.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', dest='csv_path', default=DEFAULT_SOURCE, help='Path to source CSV file.')
        parser.add_argument('--truncate', action='store_true', help='Purge existing rows before seeding.')
        parser.add_argument('--limit', type=int, default=0, help='Limit rows (for testing).')

    def handle(self, *args, **options):
        path = options['csv_path']
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'Source CSV not found: {path}'))
            sys.exit(1)
        if options['truncate']:
            ZipCode.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing ZipCode rows truncated.'))
        count_existing = ZipCode.objects.count()
        inserted = 0
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if options['limit'] and inserted >= options['limit']:
                    break
                z = (row.get('zip') or row.get('Zip') or '').strip()
                city = (row.get('city') or row.get('City') or '').strip()
                state = (row.get('state') or row.get('State') or '').strip()
                lat = (row.get('latitude') or row.get('Latitude') or '').strip()
                lng = (row.get('longitude') or row.get('Longitude') or '').strip()
                if not (z and city and state and lat and lng):
                    continue
                if len(z) != 5 or not z.isdigit():
                    continue
                if ZipCode.objects.filter(pk=z).exists():
                    continue
                try:
                    ZipCode.objects.create(zip=z, city=city.title(), state=state.upper(), latitude=lat, longitude=lng)
                    inserted += 1
                except Exception:
                    continue
        self.stdout.write(self.style.SUCCESS(f'Seed complete: existing={count_existing} inserted={inserted} total={ZipCode.objects.count()}'))
