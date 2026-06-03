"""
Camera Serializers
"""
from rest_framework import serializers
from .models import Camera
from apps.accounts.validation import (
    validate_camera_location,
    validate_camera_name,
    validate_short_text,
    validate_stream_url,
)


class CameraSerializer(serializers.ModelSerializer):
    """Camera serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    
    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'rtsp_url', 'location', 'zone',
            'status', 'created_at', 'ai_monitoring_enabled',
        ]
        read_only_fields = ['id', 'created_at', 'status', 'ai_monitoring_enabled']
    
    def validate_status(self, value):
        """Validate status"""
        if value not in ['ONLINE', 'OFFLINE']:
            raise serializers.ValidationError("Status must be ONLINE or OFFLINE")
        return value

    def validate_name(self, value):
        return validate_camera_name(value)

    def validate_rtsp_url(self, value):
        return validate_stream_url(value)

    def validate_location(self, value):
        return validate_camera_location(value)

    def validate_zone(self, value):
        if value in (None, ""):
            return value
        return validate_short_text(value, "Zone", 2, 150)


class CameraCreateSerializer(serializers.ModelSerializer):
    """Camera creation serializer"""
    
    class Meta:
        model = Camera
        fields = ['name', 'rtsp_url', 'location', 'zone', 'status']

    def validate_name(self, value):
        return validate_camera_name(value)

    def validate_rtsp_url(self, value):
        return validate_stream_url(value)

    def validate_location(self, value):
        return validate_camera_location(value)

    def validate_zone(self, value):
        if value in (None, ""):
            return value
        return validate_short_text(value, "Zone", 2, 150)


class CameraStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating camera status"""
    status = serializers.ChoiceField(choices=['ONLINE', 'OFFLINE'])

