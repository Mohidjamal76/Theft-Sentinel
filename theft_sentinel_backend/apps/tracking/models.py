"""
Tracking Record Model

Stores per-person sightings from the AI pipeline's DeepSORT + ReID system.
Each record represents one confirmed track sighting at a specific camera,
enriched with the detection confidence and the camera's location snapshot.
"""
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class TrackingRecord(models.Model):
    """Tracking Record model for person tracking feature vectors"""
    
    id = ObjectIdAutoField(primary_key=True)
    person_id = models.CharField(max_length=255, db_index=True)
    camera_id = models.ForeignKey(
        'cameras.Camera',
        on_delete=models.CASCADE,
        related_name='tracking_records'
    )
    vector = models.JSONField(default=dict)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # --- Fields consumed by the frontend Records table ---
    confidence = models.FloatField(
        default=0.0,
        help_text="Detection confidence from YOLO (0-1)"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Snapshot of the camera location at recording time"
    )
    
    # Extra metadata for richer querying
    global_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Cross-camera global identity ID from ReID/FAISS"
    )
    x3d_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Latest X3D theft probability at time of recording"
    )
    bbox = models.JSONField(
        default=list,
        help_text="Bounding box [x1, y1, x2, y2]"
    )
    
    class Meta:
        db_table = 'tracking_records'
        verbose_name = 'Tracking Record'
        verbose_name_plural = 'Tracking Records'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['person_id', '-timestamp']),
        ]
    
    def __str__(self):
        cam_name = getattr(self.camera_id, 'name', str(self.camera_id_id))
        return f"Person {self.person_id} - {cam_name} at {self.timestamp}"
