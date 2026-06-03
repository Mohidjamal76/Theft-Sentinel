import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.accounts.serializers import validate_password_strength
from apps.accounts.validation import (
    normalize_email,
    normalize_pakistani_phone,
    normalize_username,
    validate_address,
    validate_company_name,
    validate_name,
    validate_reason,
)
from .models import Tenant, Branch, SuperAdminProfile, BranchPasswordResetRequest
from .cnic_registry import (
    branch_owner,
    partner_owner,
    validate_unique_cnic,
    validate_unique_cnic_list,
)

User = get_user_model()


def validate_username_format(value):
    return normalize_username(value)


class SuperAdminExistsSerializer(serializers.Serializer):
    exists = serializers.BooleanField()


class SuperAdminCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, min_length=8)
    partners_count = serializers.IntegerField(min_value=0, max_value=3)
    partner_names = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_empty=True,
        required=False,
        default=list,
    )
    partner_cnics = serializers.ListField(
        child=serializers.CharField(max_length=30),
        allow_empty=True,
        required=False,
        default=list,
    )

    def validate_password(self, value):
        validate_password_strength(value)
        return value

    def validate_full_name(self, value):
        return validate_name(value)

    def validate_phone_number(self, value):
        return normalize_pakistani_phone(value, required=True)

    def _reusable_inactive_super_admin(self):
        email = self.initial_data.get("email") if hasattr(self, "initial_data") else None
        if not email:
            return None
        return User.objects.filter(
            email__iexact=str(email).strip().lower(),
            role="SUPER_ADMIN",
            is_active=False,
        ).first()

    def validate_username(self, value):
        value = validate_username_format(value)
        existing = self._reusable_inactive_super_admin()
        queryset = User.objects.filter(username__iexact=value, branch__isnull=True)
        if existing is not None:
            queryset = queryset.exclude(pk=existing.pk)
        if queryset.exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        value = normalize_email(value)
        existing = User.objects.filter(
            email__iexact=value,
            role="SUPER_ADMIN",
            is_active=False,
        ).first()
        queryset = User.objects.filter(email__iexact=value)
        if existing is not None:
            queryset = queryset.exclude(pk=existing.pk)
        if queryset.exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate(self, attrs):
        count = attrs.get("partners_count", 0)
        names = attrs.get("partner_names") or []
        cnics = attrs.get("partner_cnics") or []
        if count != len(names) or count != len(cnics):
            raise serializers.ValidationError(
                {"partners_count": "Partner count must match provided names and CNICs."}
            )
        attrs["partner_names"] = [validate_name(name) for name in names]
        attrs["partner_cnics"] = validate_unique_cnic_list(cnics)
        return attrs


class TenantBranchRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=150)
    branch_name = serializers.CharField(max_length=150)
    admin_name = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=150)
    cnic = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=30)
    company_address = serializers.CharField(max_length=300)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password_strength(value)
        return value

    def validate_company_name(self, value):
        return validate_company_name(value)

    def validate_branch_name(self, value):
        return validate_company_name(value)

    def validate_admin_name(self, value):
        return validate_name(value)

    def validate_username(self, value):
        return validate_username_format(value)

    def validate_cnic(self, value):
        return validate_unique_cnic(value)

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_phone_number(self, value):
        return normalize_pakistani_phone(value, required=True)

    def validate_company_address(self, value):
        return validate_address(value)


class BranchSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    tenant_id = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    company_address = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            "id",
            "tenant_id",
            "company_name",
            "company_address",
            "branch_name",
            "admin_name",
            "admin_cnic",
            "admin_email",
            "admin_phone",
            "status",
            "created_at",
        ]

    def get_tenant_id(self, obj):
        return str(obj.tenant_id) if hasattr(obj, "tenant_id") else (str(obj.tenant.id) if obj.tenant else None)

    def get_company_name(self, obj):
        return obj.tenant.company_name if obj.tenant else None

    def get_company_address(self, obj):
        return obj.tenant.company_address if obj.tenant else None


class BranchStatusUpdateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "suspend", "reapprove"])


class SuperAdminProfileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    user_id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = SuperAdminProfile
        fields = [
            "id",
            "user_id",
            "email",
            "full_name",
            "phone_number",
            "partners_count",
            "partners",
            "created_at",
        ]

    def get_user_id(self, obj):
        return str(obj.user.id) if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None


class SuperAdminProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100, required=False)
    phone_number = serializers.CharField(max_length=30, required=False)
    partners_count = serializers.IntegerField(min_value=0, max_value=3, required=False)
    partner_names = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=True), required=False, allow_empty=True
    )
    partner_cnics = serializers.ListField(
        child=serializers.CharField(max_length=30, allow_blank=True), required=False, allow_empty=True
    )

    def validate(self, attrs):
        if "full_name" in attrs:
            attrs["full_name"] = validate_name(attrs["full_name"])
        if "phone_number" in attrs:
            attrs["phone_number"] = normalize_pakistani_phone(attrs["phone_number"], required=True)
        if "partners_count" in attrs:
            count = attrs["partners_count"]
            names = [name.strip() for name in attrs.get("partner_names") or []]
            cnics = [cnic.strip() for cnic in attrs.get("partner_cnics") or []]
            if names is None or cnics is None:
                raise serializers.ValidationError(
                    "partner_names and partner_cnics are required when updating partners_count."
                )
            if count != len(names) or count != len(cnics):
                raise serializers.ValidationError(
                    {"partners_count": "Partner count must match provided names and CNICs."}
                )
            errors = {}
            blank_names = [f"Partner name #{idx + 1} is required." for idx, name in enumerate(names) if not name]
            blank_cnics = [f"Partner CNIC #{idx + 1} is required." for idx, cnic in enumerate(cnics) if not cnic]
            if blank_names:
                errors["partner_names"] = blank_names
            if blank_cnics:
                errors["partner_cnics"] = blank_cnics
            if errors:
                raise serializers.ValidationError(errors)
            attrs["partner_names"] = [validate_name(name) for name in names]
            request = self.context.get("request")
            profile = getattr(getattr(request, "user", None), "super_admin_profile", None)
            allowed = []
            if profile is not None:
                allowed = [partner_owner(profile.id, idx) for idx in range(count)]
            attrs["partner_cnics"] = validate_unique_cnic_list(cnics, allowed_owners=allowed)
        return attrs


class BranchAdminProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField(source="admin_name")
    email = serializers.EmailField(source="admin_email")
    cnic = serializers.CharField(source="admin_cnic")
    phone_number = serializers.CharField(source="admin_phone", allow_blank=True)
    company_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField()
    address = serializers.SerializerMethodField()
    registration_date = serializers.DateTimeField(source="created_at")

    def get_company_name(self, obj):
        return obj.tenant.company_name if obj.tenant else None

    def get_address(self, obj):
        return obj.tenant.company_address if obj.tenant else ""


class BranchAdminProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    cnic = serializers.CharField(max_length=30)
    phone_number = serializers.CharField(max_length=30)
    company_name = serializers.CharField(max_length=150)
    branch_name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=300)

    def validate_full_name(self, value):
        return validate_name(value)

    def validate_cnic(self, value):
        request = self.context.get("request")
        branch = getattr(getattr(request, "user", None), "branch", None)
        allowed = [branch_owner(branch.id)] if branch is not None else None
        return validate_unique_cnic(value, allowed_owners=allowed)

    def validate_phone_number(self, value):
        return normalize_pakistani_phone(value, required=True)

    def validate_company_name(self, value):
        return validate_company_name(value)

    def validate_branch_name(self, value):
        return validate_company_name(value)

    def validate_address(self, value):
        return validate_address(value)

    def validate_email(self, value):
        value = normalize_email(value)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        qs = User.objects.filter(email__iexact=value)
        if user and getattr(user, "pk", None):
            qs = qs.exclude(pk=user.pk)
        if qs.exists():
            raise serializers.ValidationError("Email already exists.")
        return value


class SuperAdminForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return normalize_email(value)


class BranchAdminResetRequestCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reason = serializers.CharField()

    def validate_email(self, value):
        return normalize_email(value)

    def validate_reason(self, value):
        return validate_reason(value)


class BranchPasswordResetRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    user_email = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    branch_id = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = BranchPasswordResetRequest
        fields = [
            "id",
            "user_email",
            "username",
            "branch_id",
            "branch_name",
            "company_name",
            "reason",
            "status",
            "created_at",
            "reviewed_at",
        ]

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_username(self, obj):
        return obj.user.username if obj.user else None

    def get_branch_id(self, obj):
        return str(obj.branch.id) if obj.branch else None

    def get_branch_name(self, obj):
        return obj.branch.branch_name if obj.branch else None

    def get_company_name(self, obj):
        return obj.branch.tenant.company_name if obj.branch and obj.branch.tenant else None

