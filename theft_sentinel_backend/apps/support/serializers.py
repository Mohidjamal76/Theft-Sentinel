from rest_framework import serializers

from apps.accounts.validation import validate_message, validate_reason
from .models import SupportQuery


class SupportQueryCreateSerializer(serializers.Serializer):
    message = serializers.CharField()

    def validate_message(self, value):
        return validate_message(value)


class SupportQuerySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    sender_email = serializers.SerializerMethodField()
    sender_username = serializers.SerializerMethodField()
    sender_role = serializers.SerializerMethodField()
    branch_id = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportQuery
        fields = [
            "id",
            "sender_email",
            "sender_username",
            "sender_role",
            "branch_id",
            "branch_name",
            "company_name",
            "message",
            "answer",
            "status",
            "created_at",
            "answered_at",
        ]

    def get_sender_email(self, obj):
        return obj.sender.email if obj.sender else None

    def get_sender_username(self, obj):
        return obj.sender.username if obj.sender else None

    def get_sender_role(self, obj):
        return obj.sender.role if obj.sender else None

    def get_branch_id(self, obj):
        return str(obj.branch.id) if obj.branch else None

    def get_branch_name(self, obj):
        return obj.branch.branch_name if obj.branch else None

    def get_company_name(self, obj):
        return obj.branch.tenant.company_name if obj.branch and obj.branch.tenant else None


class BranchAdminQueryActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve_to_super_admin", "delete"])


class SuperAdminQueryAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()

    def validate_answer(self, value):
        return validate_reason(value)

