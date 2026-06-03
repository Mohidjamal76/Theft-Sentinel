"""
Surveillance Event Model
"""
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class SurveillanceEvent(models.Model):
    """Surveillance Event model for AI-detected events"""
    
    id = ObjectIdAutoField(primary_key=True)
    camera_id = models.ForeignKey(
        'cameras.Camera',
        on_delete=models.CASCADE,
        related_name='surveillance_events'
    )
    event_type = models.CharField(max_length=100, db_index=True)
    frame_url = models.CharField(max_length=512, blank=True)
    ai_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'surveillance_events'
        verbose_name = 'Surveillance Event'
        verbose_name_plural = 'Surveillance Events'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.camera_id.name} at {self.created_at}"

