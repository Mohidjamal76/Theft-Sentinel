"""
Camera Model
"""
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Camera(models.Model):
    """Camera model for surveillance cameras"""
    
    STATUS_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
    ]
    
    id = ObjectIdAutoField(primary_key=True)
    branch = models.ForeignKey(
        "tenancy.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cameras",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    rtsp_url = models.CharField(max_length=512)
    location = models.CharField(max_length=255)
    zone = models.CharField(max_length=100, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OFFLINE', db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Feed health tracking (feed-driven status) - OBSERVES feed without modifying pipeline
    last_feed_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Last time feed was confirmed active (updated by external feed checker)"
    )

    # AI monitoring persistence — stored in MongoDB so the toggle survives
    # server restarts and full page reloads, exactly like camera status does.
    ai_monitoring_enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether AI continuous monitoring is enabled for this camera"
    )
    
    class Meta:
        db_table = 'cameras'
        verbose_name = 'Camera'
        verbose_name_plural = 'Cameras'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.location} ({self.status})"

