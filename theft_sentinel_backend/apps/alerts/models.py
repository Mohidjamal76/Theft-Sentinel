"""
Alert Model
"""
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Alert(models.Model):
    """Alert model for security alerts"""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACKED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    ]
    
    id = ObjectIdAutoField(primary_key=True)
    camera_id = models.ForeignKey(
        'cameras.Camera',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    alert_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    metadata = models.JSONField(default=dict)
    video_url = models.URLField(null=True, blank=True)
    video_public_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'alerts'
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.alert_type} - {self.camera_id.name} ({self.status})"

