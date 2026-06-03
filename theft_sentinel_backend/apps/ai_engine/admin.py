"""
AI Engine Admin
"""
from django.contrib import admin
from .models import AIInference, DetectionTrack


@admin.register(AIInference)
class AIInferenceAdmin(admin.ModelAdmin):
    list_display = ['id', 'camera_id', 'classification', 'confidence', 'processing_time_ms', 'timestamp']
    list_filter = ['classification', 'timestamp']
    search_fields = ['camera_id__name', 'classification']
    readonly_fields = ['id', 'timestamp']
    date_hierarchy = 'timestamp'


@admin.register(DetectionTrack)
class DetectionTrackAdmin(admin.ModelAdmin):
    list_display = ['id', 'camera_id', 'track_id', 'object_type', 'ml_theft_score', 'is_suspicious', 'is_active', 'last_seen']
    list_filter = ['object_type', 'is_suspicious', 'is_active']
    search_fields = ['camera_id__name', 'track_id']
    readonly_fields = ['id', 'first_seen', 'last_seen']
