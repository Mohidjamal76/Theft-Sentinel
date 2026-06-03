"""
Django management command to periodically check camera feed health.

This command:
- Tests each camera feed to verify it's actually accessible
- Never changes camera ONLINE/OFFLINE state
- Runs every 5 seconds (should be called via cron or task scheduler)

Usage:
    python manage.py check_camera_feeds

For periodic execution (every 5 seconds), use:
    - Django-crontab
    - Celery periodic tasks
    - System cron
    - Or call from a background thread/service
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cameras.services import check_all_camera_feeds

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Checks camera feed health without changing camera status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"[{timezone.now().isoformat()}] Starting camera feed health check..."))
        
        try:
            # Perform camera health check
            health_stats = check_all_camera_feeds()
            
            self.stdout.write(self.style.SUCCESS(
                f"Feed check complete: {health_stats['checked']} cameras checked, "
                f"{health_stats.get('feeds_live', 0)} feeds live, "
                f"{health_stats['updated']} statuses updated."
            ))
            
        except Exception as e:
            logger.exception("Error during check_camera_feeds command:")
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))

