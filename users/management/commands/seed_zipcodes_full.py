from django.core.management.base import BaseCommand
from django.db import transaction
from users.models_profile import ZipCode

import sqlite3
import os
import csv

BATCH_SIZE = 1000

class Command(BaseCommand):
    help = "Populate ZipCode table with a comprehensive ZIP CSV (set env ZIPCODE_FULL_SOURCE)."

    def add_arguments(self, parser):
        parser.add_argument('--truncate', action='store_true', help='Purge existing rows before loading.')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of rows (for testing).')
        parser.add_argument('--dry-run', action='store_true', help='Show counts without inserting.')

    def handle(self, *args, **opts):
        truncate = opts['truncate']
        limit = opts['limit']
        dry = opts['dry_run']

        # Expect an environment variable pointing to a comprehensive ZIP CSV (zipcode,lat,lng,major_city,state)
        csv_path = os.environ.get('ZIPCODE_FULL_SOURCE')
        if not csv_path or not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR("Set ZIPCODE_FULL_SOURCE to a CSV with columns: zipcode,lat,lng,major_city,state"))
            return

        if truncate and not dry:
            ZipCode.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing ZipCode rows truncated.'))
        existing_before = ZipCode.objects.count()

        rows_iter = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                zipc = (row.get('zipcode') or row.get('zip') or '').strip()
                lat = row.get('lat') or row.get('latitude')
                lng = row.get('lng') or row.get('longitude')
                city = (row.get('major_city') or row.get('city') or '').strip()
                state = (row.get('state') or '').strip()
                if zipc and lat and lng and city and state and len(zipc)==5 and zipc.isdigit():
                    rows_iter.append((zipc, lat, lng, city, state))
        total_source = len(rows_iter)
        if limit:
            rows_iter = rows_iter[:limit]
        to_insert = []
        inserted = 0
        seen = set(ZipCode.objects.values_list('zip', flat=True)) if existing_before else set()

        if dry:
            self.stdout.write(self.style.SUCCESS(f"Dry run: would process {len(rows_iter)}/{total_source} rows. Existing: {existing_before}"))
            return

        for (zipc, lat, lng, city, state) in rows_iter:
            if not zipc or zipc in seen:
                continue
            seen.add(zipc)
            to_insert.append(ZipCode(zip=zipc, city=(city or '').title(), state=(state or '').upper(), latitude=str(lat), longitude=str(lng)))
            if len(to_insert) >= BATCH_SIZE:
                with transaction.atomic():
                    ZipCode.objects.bulk_create(to_insert, ignore_conflicts=True)
                inserted += len(to_insert)
                to_insert.clear()
                if inserted % (BATCH_SIZE * 10) == 0:
                    self.stdout.write(f"Inserted {inserted} ...")
        if to_insert:
            with transaction.atomic():
                ZipCode.objects.bulk_create(to_insert, ignore_conflicts=True)
            inserted += len(to_insert)
        self.stdout.write(self.style.SUCCESS(f"Full load complete: existing_before={existing_before} inserted={inserted} total={ZipCode.objects.count()} source_rows={total_source}"))
