from django.core.management.base import BaseCommand
from users.models_profile import GalleryImage
from users.models_blog import BlogPost
from users.image_utils import process_generic_image, PIPELINE_VERSION

class Command(BaseCommand):
    help = "Backfill / regenerate variant metadata for gallery and blog images"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force reprocess even if metadata exists')
        parser.add_argument('--limit', type=int, default=None, help='Limit total images processed (gallery + blog)')

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']
        processed = 0
        skipped = 0

        def maybe_process(obj, field_name='image_meta'):
            nonlocal processed, skipped
            if limit and processed >= limit:
                return
            existing = getattr(obj, field_name, None) or {}
            if existing and not force:
                # Skip if current pipeline version already applied
                if existing.get('pipeline_version') == PIPELINE_VERSION:
                    skipped += 1
                    return
            try:
                meta = process_generic_image(obj.image)
                type(obj).objects.filter(pk=obj.pk).update(**{field_name: meta})
                processed += 1
                if processed % 50 == 0:
                    self.stdout.write(f"Processed {processed} images so far ...")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed processing id={obj.pk} ({type(obj).__name__}): {e}"))

        for gi in GalleryImage.objects.exclude(image='').iterator():
            maybe_process(gi, 'image_meta')
            if limit and processed >= limit:
                break

        if not limit or processed < limit:
            for bp in BlogPost.objects.exclude(image='').iterator():
                maybe_process(bp, 'image_meta')
                if limit and processed >= limit:
                    break

        self.stdout.write(self.style.SUCCESS(f"Done. processed={processed} skipped={skipped}"))
