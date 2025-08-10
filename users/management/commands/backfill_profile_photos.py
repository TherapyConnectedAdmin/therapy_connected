from django.core.management.base import BaseCommand
from users.models_profile import TherapistProfile
from users.image_utils import process_profile_photo, process_profile_photo_storage, PIPELINE_VERSION
from pathlib import Path

class Command(BaseCommand):
    help = "Generate / regenerate profile photo variants and metadata for all therapists"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force reprocess even if metadata exists (ignores hashes)')
        parser.add_argument('--reprocess-changed', action='store_true', help='Only reprocess if content hash changed or pipeline version bumped')
        parser.add_argument('--limit', type=int, default=None, help='Limit number processed')

    def handle(self, *args, **options):
        force = options['force']
        reprocess_changed = options['reprocess_changed']
        limit = options['limit']
        qs = TherapistProfile.objects.exclude(profile_photo='').exclude(profile_photo__isnull=True)
        total = qs.count()
        processed = 0
        skipped = 0
        for idx, tp in enumerate(qs.iterator(), start=1):
            if limit and processed >= limit:
                break
            existing = tp.profile_photo_meta or {}
            if not force and existing.get('variants'):
                if reprocess_changed:
                    # Reprocess only if pipeline version mismatch or file hash mismatch
                    existing_version = existing.get('pipeline_version')
                    existing_hash = (existing.get('original') or {}).get('sha256')
                    needs = False
                    if existing_version != PIPELINE_VERSION:
                        needs = True
                    else:
                        # Compute fresh meta to compare hash quickly (we still must process to get hash) - optimize by local path check
                        try:
                            path = tp.profile_photo.path
                            meta_probe = process_profile_photo(path)
                        except Exception:
                            meta_probe = process_profile_photo_storage(tp.profile_photo)
                        new_hash = (meta_probe.get('original') or {}).get('sha256')
                        if existing_hash and new_hash and existing_hash != new_hash:
                            needs = True
                        # If not needed after probe, skip
                        if not needs:
                            skipped += 1
                            continue
                        # Use the fully processed probe result as new_meta
                        meta = meta_probe
                else:
                    skipped += 1
                    continue
            try:
                if 'meta' not in locals():  # not already produced via probe
                    path = tp.profile_photo.path
                    if not Path(path).exists():
                        raise FileNotFoundError(path)
                    meta = process_profile_photo(path)
            except Exception:
                # Remote storage or missing local path: use storage handler
                meta = process_profile_photo_storage(tp.profile_photo)
            tp.profile_photo_meta = meta
            tp.save(update_fields=['profile_photo_meta'])
            processed += 1
            if processed % 25 == 0:
                self.stdout.write(f"Processed {processed} so far ...")
        self.stdout.write(self.style.SUCCESS(f"Done. Total={total} processed={processed} skipped={skipped}"))
