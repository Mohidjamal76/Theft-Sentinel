import logging

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .models import Alert

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Alert)
def remove_alert_video_from_cloudinary(sender, instance, **kwargs):
    try:
        from .cloudinary_video import (
            delete_cloudinary_video,
            delete_cloudinary_video_from_url,
        )

        public_id = getattr(instance, "video_public_id", None) or ""
        if public_id:
            delete_cloudinary_video(public_id)
            return
        url = getattr(instance, "video_url", None) or ""
        if url:
            delete_cloudinary_video_from_url(url)
    except Exception:
        logger.exception("Failed to delete Cloudinary video for alert %s", instance.pk)
