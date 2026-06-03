"""
Incident Serializers
"""
from rest_framework import serializers
from .models import Incident
from apps.alerts.serializers import AlertSerializer
from apps.accounts.serializers import UserSerializer
from apps.accounts.validation import validate_message


class IncidentSerializer(serializers.ModelSerializer):
    """Incident serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    alert_id = serializers.SerializerMethodField()  # Convert ObjectId to string
    assigned_to = serializers.SerializerMethodField()  # Convert ObjectId to string
    assigned_by = serializers.SerializerMethodField()  # Convert ObjectId to string
    alert_details = AlertSerializer(source='alert_id', read_only=True)
    assigned_to_details = UserSerializer(source='assigned_to', read_only=True)
    assigned_by_details = UserSerializer(source='assigned_by', read_only=True)
    detection_clip_url = serializers.SerializerMethodField()
    detection_clip_metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = Incident
        fields = [
            'id', 'alert_id', 'alert_details', 'assigned_to', 'assigned_to_details',
            'assigned_by', 'assigned_by_details', 'status', 'notes',
            'detection_clip_url', 'detection_clip_metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_alert_id(self, obj):
        """Convert alert ObjectId to string"""
        return str(obj.alert_id.id) if obj.alert_id else None
    
    def get_assigned_to(self, obj):
        """Convert assigned_to ObjectId to string"""
        return str(obj.assigned_to.id) if obj.assigned_to else None
    
    def get_assigned_by(self, obj):
        """Convert assigned_by ObjectId to string"""
        return str(obj.assigned_by.id) if obj.assigned_by else None

    def get_detection_clip_url(self, obj):
        alert = getattr(obj, 'alert_id', None)
        return getattr(alert, 'video_url', None) if alert else None

    def get_detection_clip_metadata(self, obj):
        alert = getattr(obj, 'alert_id', None)
        if not alert:
            return None
        metadata = getattr(alert, 'metadata', None) or {}
        return {
            'available': bool(getattr(alert, 'video_url', None)),
            'public_id': getattr(alert, 'video_public_id', None),
            'alert_timestamp': alert.timestamp.isoformat() if alert.timestamp else None,
            'detected_by': metadata.get('detected_by'),
            'confidence': metadata.get('confidence'),
        }


class IncidentCreateSerializer(serializers.ModelSerializer):
    """Incident creation serializer"""
    
    class Meta:
        model = Incident
        fields = ['alert_id', 'assigned_to', 'notes']


class IncidentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating incident status"""
    status = serializers.ChoiceField(choices=['CREATED', 'ASSIGNED', 'ACKNOWLEDGED', 'RESOLVED'])
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_notes(self, value):
        if not value:
            return ''
        return validate_message(value, min_length=1, max_length=1000)


class IncidentAssignSerializer(serializers.Serializer):
    """Serializer for assigning incident to user"""
    assigned_to = serializers.CharField()  # MongoDB ObjectId as string
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_notes(self, value):
        if not value:
            return ''
        return validate_message(value, min_length=1, max_length=1000)

