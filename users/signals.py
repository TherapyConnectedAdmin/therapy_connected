from django.db.models.signals import post_save
from django.dispatch import receiver
from .models_profile import TherapistProfile, GalleryImage
from .models_blog import BlogPost
from .image_utils import (
    process_profile_photo,
    process_profile_photo_storage,
    process_generic_image,
    ImageQualityFlags,
    PIPELINE_VERSION,
)
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=TherapistProfile)
def generate_profile_photo_variants(sender, instance: TherapistProfile, created, update_fields=None, **kwargs):
    """Generate image variants after profile save if a photo exists.
    Avoid infinite recursion by skipping when only profile_photo_meta was updated.
    """
    # If this save only updated meta, skip
    if update_fields and set(update_fields) == {"profile_photo_meta"}:
        return
    if not instance.profile_photo:
        return
    try:
        existing = instance.profile_photo_meta or {}
        # If existing meta has current pipeline version and a content hash, we can attempt a short-circuit
        # (Skip only if file hash matches. For storage without path this still re-hashes inside processor.)
        try:
            current_hash = existing.get('original', {}).get('sha256')
        except Exception:
            current_hash = None

        # Process image (local or remote)
        try:
            path = instance.profile_photo.path
            new_meta = process_profile_photo(path)
        except Exception:
            new_meta = process_profile_photo_storage(instance.profile_photo)

        new_hash = new_meta.get('original', {}).get('sha256')
        if (existing and existing.get('pipeline_version') == PIPELINE_VERSION and current_hash and new_hash and current_hash == new_hash):
            # Skip update; identical content & pipeline version
            return
        if existing != new_meta:
            TherapistProfile.objects.filter(pk=instance.pk).update(profile_photo_meta=new_meta)
    except Exception as e:
        logger.warning("Failed to process profile photo for therapist %s: %s", instance.pk, e)


@receiver(post_save, sender=GalleryImage)
def generate_gallery_image_variants(sender, instance: GalleryImage, created, update_fields=None, **kwargs):
    if not instance.image:
        return
    # Skip if only meta updated
    if update_fields and set(update_fields) == {"image_meta"}:
        return
    try:
        existing = instance.image_meta or {}
        try:
            new_meta = process_generic_image(instance.image)
        except Exception as e:
            logger.warning("Gallery image process fail id=%s: %s", instance.pk, e)
            return
        if existing and existing.get('pipeline_version') == PIPELINE_VERSION and existing.get('original', {}).get('sha256') == new_meta.get('original', {}).get('sha256'):
            return
        if existing != new_meta:
            GalleryImage.objects.filter(pk=instance.pk).update(image_meta=new_meta)
    except Exception as e:
        logger.warning("Failed to process gallery image %s: %s", instance.pk, e)


@receiver(post_save, sender=BlogPost)
def generate_blog_image_variants(sender, instance: BlogPost, created, update_fields=None, **kwargs):
    if not instance.image:
        return
    if update_fields and set(update_fields) == {"image_meta"}:
        return
    try:
        existing = instance.image_meta or {}
        try:
            new_meta = process_generic_image(instance.image)
        except Exception as e:
            logger.warning("Blog image process fail id=%s: %s", instance.pk, e)
            return
        if existing and existing.get('pipeline_version') == PIPELINE_VERSION and existing.get('original', {}).get('sha256') == new_meta.get('original', {}).get('sha256'):
            return
        if existing != new_meta:
            BlogPost.objects.filter(pk=instance.pk).update(image_meta=new_meta)
    except Exception as e:
        logger.warning("Failed to process blog image %s: %s", instance.pk, e)
