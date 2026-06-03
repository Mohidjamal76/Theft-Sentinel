"""
Tracking Record Serializers
"""
from rest_framework import serializers
from .models import TrackingRecord
from apps.cameras.serializers import CameraSerializer


class TrackingRecordSerializer(serializers.ModelSerializer):
    """Tracking Record serializer — read-only, includes nested camera info"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    camera_id = serializers.CharField(source='camera_id_id', read_only=True)
    camera_details = CameraSerializer(source='camera_id', read_only=True)
    camera_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TrackingRecord
        fields = [
            'id', 'person_id', 'camera_id', 'camera_name', 'camera_details',
            'vector', 'timestamp', 'confidence', 'location',
            'global_id', 'x3d_score', 'bbox',
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_camera_name(self, obj):
        """Return the camera's name for easy frontend display."""
        try:
            return obj.camera_id.name
        except Exception:
            return str(obj.camera_id_id)


class TrackingRecordCreateSerializer(serializers.ModelSerializer):
    """Tracking Record creation serializer"""
    
    class Meta:
        model = TrackingRecord
        fields = [
            'person_id', 'camera_id', 'vector',
            'confidence', 'location', 'global_id', 'x3d_score', 'bbox',
        ]
    
    def validate_vector(self, value):
        """Ensure vector is a dict or list"""
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Vector must be a dictionary or list")
        return value

    def validate_confidence(self, value):
        if value is not None and not 0 <= value <= 1:
            raise serializers.ValidationError("Confidence must be between 0.0 and 1.0.")
        return value

    def validate_x3d_score(self, value):
        if value is not None and not 0 <= value <= 1:
            raise serializers.ValidationError("X3D score must be between 0.0 and 1.0.")
        return value
