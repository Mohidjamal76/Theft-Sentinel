"""
AI Engine API Serializers
"""
from rest_framework import serializers
from apps.ai_engine.models import AIInference, DetectionTrack


class FrameAnalysisRequestSerializer(serializers.Serializer):
    """Request serializer for frame analysis"""
    frame = serializers.CharField(
        help_text="Base64 encoded image frame (with or without data URL prefix)"
    )
    camera_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Camera ID (optional)"
    )
    save_to_db = serializers.BooleanField(
        default=True,
        help_text="Whether to save results to database"
    )
    create_alert_on_theft = serializers.BooleanField(
        default=True,
        help_text="Whether to create alert if theft detected"
    )


class CameraProcessRequestSerializer(serializers.Serializer):
    """Request serializer for processing camera stream"""
    camera_id = serializers.CharField(
        required=True,
        help_text="Camera ID to process"
    )
    save_to_db = serializers.BooleanField(
        default=True,
        help_text="Whether to save results to database"
    )
    create_alert_on_theft = serializers.BooleanField(
        default=True,
        help_text="Whether to create alert if theft detected"
    )


class DetectionSerializer(serializers.Serializer):
    """Detection result serializer"""
    bbox = serializers.ListField(
        child=serializers.FloatField(),
        help_text="Bounding box [x1, y1, x2, y2]"
    )
    confidence = serializers.FloatField()
    class_name = serializers.CharField(source='class')
    class_id = serializers.IntegerField()


class PoseSerializer(serializers.Serializer):
    """Pose result serializer"""
    track_id = serializers.IntegerField()
    keypoints = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    confidence = serializers.FloatField()
    features = serializers.DictField(required=False)


class TrackSerializer(serializers.Serializer):
    """Track result serializer"""
    track_id = serializers.IntegerField()
    bbox = serializers.ListField(child=serializers.FloatField())
    class_name = serializers.CharField(source='class')
    confidence = serializers.FloatField()
    dwell_time = serializers.IntegerField()
    ml_score = serializers.FloatField()


class SuspiciousTrackSerializer(serializers.Serializer):
    """Suspicious track details"""
    track_id = serializers.IntegerField()
    ml_score = serializers.FloatField()
    behavior = serializers.DictField()


class AnalysisResponseSerializer(serializers.Serializer):
    """Response serializer for frame analysis"""
    detections = DetectionSerializer(many=True)
    poses = PoseSerializer(many=True)
    tracks = TrackSerializer(many=True)
    classification = serializers.CharField()
    confidence = serializers.FloatField()
    suspicious_tracks = SuspiciousTrackSerializer(many=True)
    frame_metadata = serializers.DictField()
    processing_time_ms = serializers.FloatField()
    alert_created = serializers.BooleanField(required=False)
    alert_id = serializers.CharField(required=False, allow_null=True)
    inference_id = serializers.CharField(required=False, allow_null=True)


class AIInferenceSerializer(serializers.ModelSerializer):
    """AI Inference model serializer"""
    id = serializers.CharField(read_only=True)
    camera_id = serializers.SerializerMethodField()
    camera_name = serializers.CharField(source='camera_id.name', read_only=True)
    alert_id = serializers.SerializerMethodField()
    
    class Meta:
        model = AIInference
        fields = [
            'id', 'camera_id', 'camera_name', 'detections', 'poses', 'tracks',
            'classification', 'confidence', 'frame_metadata', 'processing_time_ms',
            'alert_id', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_camera_id(self, obj):
        """Convert camera ObjectId to string"""
        return str(obj.camera_id.id) if obj.camera_id else None
    
    def get_alert_id(self, obj):
        """Convert alert ObjectId to string"""
        return str(obj.alert.id) if obj.alert else None


class DetectionTrackSerializer(serializers.ModelSerializer):
    """Detection Track model serializer"""
    id = serializers.CharField(read_only=True)
    camera_id = serializers.SerializerMethodField()
    camera_name = serializers.CharField(source='camera_id.name', read_only=True)
    
    class Meta:
        model = DetectionTrack
        fields = [
            'id', 'camera_id', 'camera_name', 'track_id', 'object_type',
            'first_seen', 'last_seen', 'frame_count',
            'hand_in_bag_frames', 'hand_in_torso_frames', 'fast_wrist_frames',
            'near_object_frames', 'concealment_events',
            'ml_theft_score', 'max_theft_score', 'is_suspicious', 'is_active'
        ]
        read_only_fields = ['id', 'first_seen', 'last_seen']
    
    def get_camera_id(self, obj):
        """Convert camera ObjectId to string"""
        return str(obj.camera_id.id) if obj.camera_id else None


class ModelInfoSerializer(serializers.Serializer):
    """Model information serializer"""
    detection_model = serializers.CharField()
    pose_model = serializers.CharField()
    ml_classifier = serializers.CharField()
    device = serializers.CharField()
    cuda_available = serializers.BooleanField()
    models_loaded = serializers.BooleanField()
    ml_classifier_loaded = serializers.BooleanField()

