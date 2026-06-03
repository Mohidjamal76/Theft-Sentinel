"""
Alert Serializers
"""
from rest_framework import serializers
from .models import Alert
from apps.cameras.serializers import CameraSerializer
from apps.accounts.validation import validate_message


VALID_ALERT_SEVERITIES = {'MEDIUM', 'HIGH'}


class AlertSerializer(serializers.ModelSerializer):
    """Alert serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    camera_id = serializers.SerializerMethodField()  # Convert ObjectId to string
    camera_name = serializers.SerializerMethodField()  # Get camera name
    camera_location = serializers.SerializerMethodField()  # Get camera location
    camera_details = serializers.SerializerMethodField()  # Full camera details
    
    class Meta:
        model = Alert
        fields = [
            'id', 'camera_id', 'camera_name', 'camera_location', 'camera_details',
            'alert_type', 'severity', 'timestamp', 'status', 'metadata', 'video_url',
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_camera_id(self, obj):
        """Convert camera ObjectId to string"""
        return str(obj.camera_id.id) if obj.camera_id else None
    
    def get_camera_name(self, obj):
        """Get camera name"""
        return obj.camera_id.name if obj.camera_id else "Unknown"
    
    def get_camera_location(self, obj):
        """Get camera location"""
        return obj.camera_id.location if obj.camera_id else "Unknown"
    
    def get_camera_details(self, obj):
        """Get full camera details"""
        if obj.camera_id:
            return {
                'id': str(obj.camera_id.id),
                'name': obj.camera_id.name,
                'location': obj.camera_id.location,
                'zone': obj.camera_id.zone,
                'status': obj.camera_id.status,
            }
        return None

    def validate_severity(self, value):
        value = (value or "").strip().upper()
        if value not in VALID_ALERT_SEVERITIES:
            raise serializers.ValidationError("Severity must be MEDIUM or HIGH.")
        return value


class AlertCreateSerializer(serializers.ModelSerializer):
    """Alert creation serializer"""
    
    class Meta:
        model = Alert
        fields = ['camera_id', 'alert_type', 'severity', 'metadata']
    
    def validate_metadata(self, value):
        """Ensure metadata is a dict"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a dictionary")
        return value

    def validate_alert_type(self, value):
        value = (value or "").strip()
        if len(value) < 2 or len(value) > 100:
            raise serializers.ValidationError("Alert type is required.")
        return value

    def validate_severity(self, value):
        value = (value or "").strip().upper()
        if value not in VALID_ALERT_SEVERITIES:
            raise serializers.ValidationError("Severity must be MEDIUM or HIGH.")
        return value


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts"""
    status = serializers.ChoiceField(choices=['ACKED', 'RESOLVED'])
    guard_email = serializers.EmailField(required=True)  # Guard assignment is mandatory, identified by email
    comment = serializers.CharField(required=False, allow_blank=True, default='', max_length=1000)

    def validate_comment(self, value):
        if not value:
            return ''
        return validate_message(value, min_length=1, max_length=1000)

