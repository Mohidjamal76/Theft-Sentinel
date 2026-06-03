"""
AI Engine Models
Store AI inference results and detection data
"""
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class AIInference(models.Model):
    """Store AI pipeline inference results"""
    
    id = ObjectIdAutoField(primary_key=True)
    camera_id = models.ForeignKey(
        'cameras.Camera',
        on_delete=models.CASCADE,
        related_name='ai_inferences',
        null=True,
        blank=True
    )
    
    # Detection results
    detections = models.JSONField(default=list)  # List of detected objects
    poses = models.JSONField(default=list)  # Pose keypoints
    tracks = models.JSONField(default=list)  # Tracking information
    
    # Classification results
    classification = models.CharField(max_length=50, default='normal')  # 'theft' or 'normal'
    confidence = models.FloatField(default=0.0)  # ML model confidence (0-1)
    
    # Metadata
    frame_metadata = models.JSONField(default=dict)  # Additional frame info
    processing_time_ms = models.FloatField(default=0.0)  # Time taken for inference
    
    # Related alert if theft detected
    alert = models.ForeignKey(
        'alerts.Alert',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_inferences'
    )
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = 'ai_inferences'
        verbose_name = 'AI Inference'
        verbose_name_plural = 'AI Inferences'
        ordering = ['-timestamp']
    
    def __str__(self):
        camera_name = self.camera_id.name if self.camera_id else "Unknown"
        return f"AI Inference - {camera_name} - {self.classification} ({self.confidence:.2f})"


class DetectionTrack(models.Model):
    """Store tracking information for detected objects across frames"""
    
    id = ObjectIdAutoField(primary_key=True)
    camera_id = models.ForeignKey(
        'cameras.Camera',
        on_delete=models.CASCADE,
        related_name='detection_tracks'
    )
    
    track_id = models.IntegerField()  # DeepSORT track ID
    object_type = models.CharField(max_length=50)  # 'person', 'bag', 'object'
    
    # Behavior tracking
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    frame_count = models.IntegerField(default=0)
    
    # Behavioral features (for theft detection)
    hand_in_bag_frames = models.IntegerField(default=0)
    hand_in_torso_frames = models.IntegerField(default=0)
    fast_wrist_frames = models.IntegerField(default=0)
    near_object_frames = models.IntegerField(default=0)
    concealment_events = models.IntegerField(default=0)
    
    # ML scores
    ml_theft_score = models.FloatField(default=0.0)  # Latest ML prediction
    max_theft_score = models.FloatField(default=0.0)  # Highest score recorded
    
    # Status
    is_suspicious = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'detection_tracks'
        verbose_name = 'Detection Track'
        verbose_name_plural = 'Detection Tracks'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['camera_id', 'track_id']),
            models.Index(fields=['is_active', 'is_suspicious']),
        ]
    
    def __str__(self):
        return f"Track #{self.track_id} - {self.object_type} - Camera {self.camera_id.name}"
