from django.core.management.base import BaseCommand
from django.db.models import Count
from users.models_profile import ZipCode, Location

class Command(BaseCommand):
    help = "Report health metrics for ZipCode dataset and location usage."

    def handle(self, *args, **options):
        total = ZipCode.objects.count()
        self.stdout.write(f"ZipCode rows: {total}")
        if total == 0:
            self.stdout.write(self.style.ERROR("ZipCode table empty. Run seed_zipcodes_full."))
            return
        # Basic distribution by state (top 10 states by count)
        top_states = ZipCode.objects.values('state').annotate(c=Count('state')).order_by('-c')[:10]
        self.stdout.write("Top states by ZIP count:")
        for s in top_states:
            self.stdout.write(f"  {s['state']}: {s['c']}")
        # Locations referencing unknown zips
        location_total = Location.objects.count()
        missing = Location.objects.exclude(zip__in=ZipCode.objects.values_list('zip', flat=True)).count()
        self.stdout.write(f"Locations total: {location_total}")
        self.stdout.write(f"Locations with missing ZipCode reference: {missing}")
        if missing:
            sample = Location.objects.exclude(zip__in=ZipCode.objects.values_list('zip', flat=True))[:5]
            self.stdout.write("Sample missing zips:")
            for loc in sample:
                self.stdout.write(f"  Therapist {loc.therapist_id} zip {loc.zip}")
        # Potential future metrics: avg distance query perf, stale entries, etc.
        self.stdout.write(self.style.SUCCESS("ZipCode health report complete."))
