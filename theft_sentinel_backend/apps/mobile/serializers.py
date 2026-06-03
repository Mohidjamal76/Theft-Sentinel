"""
Notification Serializers
"""
from rest_framework import serializers
from .models import Notification
from apps.accounts.serializers import UserSerializer
from apps.accounts.validation import normalize_email, normalize_pakistani_phone, validate_message


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_details', 'notification_type', 'recipient',
            'subject', 'message', 'status', 'error_message', 'created_at', 'sent_at'
        ]
        read_only_fields = ['id', 'created_at', 'sent_at']


class SendSMSSerializer(serializers.Serializer):
    """Serializer for sending SMS"""
    phone_number = serializers.CharField(max_length=20)
    message = serializers.CharField()

    def validate_phone_number(self, value):
        return normalize_pakistani_phone(value, required=True)

    def validate_message(self, value):
        return validate_message(value, min_length=1, max_length=1600)


class SendEmailSerializer(serializers.Serializer):
    """Serializer for sending Email"""
    email_address = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()

    def validate_email_address(self, value):
        return normalize_email(value)

    def validate_subject(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Subject is required.")
        return value

    def validate_message(self, value):
        return validate_message(value)


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer for bulk notifications"""
    user_ids = serializers.ListField(child=serializers.CharField())  # MongoDB ObjectId as string
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    send_sms = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=True)

    def validate_subject(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Subject is required.")
        return value

    def validate_message(self, value):
        return validate_message(value)

