"""
Feedback Serializers
"""
from rest_framework import serializers
from .models import Feedback
from apps.accounts.serializers import UserSerializer
from apps.accounts.validation import validate_message


class FeedbackSerializer(serializers.ModelSerializer):
    """Feedback serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    user_id = serializers.CharField(read_only=True)  # Convert ObjectId to string
    user_details = UserSerializer(source='user_id', read_only=True)
    
    class Meta:
        model = Feedback
        fields = ['id', 'user_id', 'user_details', 'type', 'message', 'created_at']
        read_only_fields = ['id', 'created_at', 'user_id']


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """Feedback creation serializer"""
    
    class Meta:
        model = Feedback
        fields = ['type', 'message']
    
    def validate_message(self, value):
        """Validate message is not empty"""
        return validate_message(value)

