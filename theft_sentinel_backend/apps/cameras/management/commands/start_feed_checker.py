"""
Django management command to start a background feed checker service.

This command runs continuously, checking camera feed availability every 5 seconds.
It reports health only and never changes camera ONLINE/OFFLINE state.

Usage:
    python manage.py start_feed_checker

For production, run this as a separate service/daemon.
"""
import logging
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.cameras.services import check_all_camera_feeds

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Starts a read-only feed health checker every 5 seconds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Interval in seconds between feed checks (default: 5)',
        )

    def handle(self, *args, **options):
        interval = options['interval']
        
        self.stdout.write(self.style.SUCCESS(
            f"Starting camera feed checker service (interval: {interval}s)..."
        ))
        self.stdout.write(self.style.WARNING(
            "Press Ctrl+C to stop the service"
        ))
        
        try:
            while True:
                start_time = timezone.now()
                
                # Perform camera health check
                health_stats = check_all_camera_feeds()
                
                elapsed = (timezone.now() - start_time).total_seconds()
                
                self.stdout.write(self.style.SUCCESS(
                    f"[{timezone.now().strftime('%H:%M:%S')}] "
                    f"Checked {health_stats['checked']} cameras, "
                    f"{health_stats.get('feeds_live', 0)} feeds live, "
                    f"updated {health_stats['updated']} statuses "
                    f"(took {elapsed:.2f}s)"
                ))
                
                # # Sleep for the remaining interval time
                # sleep_time = max(0, interval - elapsed)
                # if sleep_time > 0:
                #     time.sleep(sleep_time)
                # Sleep for 5 seconds
                time.sleep(5)

                    
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopping camera feed checker service..."))
        except Exception as e:
            logger.exception("Error in feed checker service:")
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))

