"""
Serializers for User and Authentication
"""
import re

from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .validation import (
    PASSWORD_ERROR,
    normalize_email,
    normalize_username,
    validate_password_value,
)

User = get_user_model()

NON_ADMIN_FORGOT_PASSWORD_MESSAGE = (
    "Only admin can change password from here. Contact admin if you have lost your password."
)

PASSWORD_COMPLEXITY_ERROR = (
    "Password must be at least 8 characters long and include at least one uppercase "
    "letter (A–Z), one lowercase letter (a–z), one number (0–9), and one special "
    "character (e.g. @, #, $, %)."
)
PASSWORD_COMPLEXITY_ERROR = PASSWORD_ERROR


def validate_password_strength(value):
    """
    Enforce password rules for set, change, and reset flows.
    Raises ValidationError with a single user-facing message if invalid.
    """
    return validate_password_value(value)


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    id = serializers.CharField(read_only=True)  # MongoDB ObjectId as string
    branch_id = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    branch_admin_name = serializers.SerializerMethodField()
    branch_admin_email = serializers.SerializerMethodField()
    branch_admin_phone = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    company_address = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'branch_id',
            'branch_name',
            'branch_admin_name',
            'branch_admin_email',
            'branch_admin_phone',
            'company_name',
            'company_address',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_role(self, value):
        """
        Ensure only one Branch Admin per branch when assigning ADMIN role.
        SUPER_ADMIN is globally unique (enforced on creation endpoint).
        """
        if value == 'ADMIN':
            branch = getattr(self.instance, "branch", None) if self.instance is not None else None
            if branch is not None:
                qs = User.objects.filter(role='ADMIN', is_active=True, branch=branch)
                if self.instance is not None:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        "Only one Admin can exist in a branch. A Branch Admin already exists for this branch."
                    )
        return value

    def validate_username(self, value):
        value = normalize_username(value)
        branch = getattr(self.instance, "branch", None) if self.instance is not None else None
        qs = User.objects.filter(username__iexact=value, branch=branch)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        value = normalize_email(value)
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def get_branch_id(self, obj):
        return str(obj.branch.id) if getattr(obj, "branch", None) else None

    def get_branch_name(self, obj):
        return getattr(obj.branch, "branch_name", None) if getattr(obj, "branch", None) else None

    def get_branch_admin_name(self, obj):
        return getattr(obj.branch, "admin_name", None) if getattr(obj, "branch", None) else None

    def get_branch_admin_email(self, obj):
        return getattr(obj.branch, "admin_email", None) if getattr(obj, "branch", None) else None

    def get_branch_admin_phone(self, obj):
        return getattr(obj.branch, "admin_phone", None) if getattr(obj, "branch", None) else None

    def get_company_name(self, obj):
        if getattr(obj, "branch", None) and getattr(obj.branch, "tenant", None):
            return obj.branch.tenant.company_name
        return None

    def get_company_address(self, obj):
        if getattr(obj, "branch", None) and getattr(obj.branch, "tenant", None):
            return obj.branch.tenant.company_address
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """User creation serializer (Admin only)"""
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'is_active']
    
    def validate_role(self, value):
        """Admin creation is branch-scoped; global uniqueness removed."""
        return value

    def validate_username(self, value):
        return normalize_username(value)

    def validate_email(self, value):
        value = normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_password(self, value):
        validate_password_strength(value)
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        branch = getattr(getattr(request, "user", None), "branch", None)
        if branch is not None:
            exists = User.objects.filter(username__iexact=attrs["username"], branch=branch).exists()
            message = "Username already exists in this branch."
        else:
            exists = User.objects.filter(username__iexact=attrs["username"], branch__isnull=True).exists()
            message = "Username already exists."
        if exists:
            raise serializers.ValidationError({"username": [message]})
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with user data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django authenticates by the unique USERNAME_FIELD (email). Keep accepting
        # the frontend's existing "username" key as a login identifier.
        self.fields[self.username_field].required = False
        self.fields['username'] = serializers.CharField(write_only=True, required=False)

    def _resolve_login_email(self, login_value, password):
        """
        Return the email Django should authenticate against.
        Username fallback respects branch-scoped usernames by using the password
        to disambiguate duplicate usernames across branches.
        """
        login_value = login_value.strip()
        if not login_value:
            return login_value

        email_user = User.objects.filter(email__iexact=login_value, is_active=True).only('email').first()
        if email_user is not None:
            return email_user.email

        matching_users = User.objects.filter(username__iexact=login_value, is_active=True)
        password_matches = [user for user in matching_users if password and user.check_password(password)]
        if len(password_matches) == 1:
            return password_matches[0].email
        return login_value
    
    def validate(self, attrs):
        login_value = attrs.get(self.username_field) or attrs.get('username')
        if not login_value:
            raise serializers.ValidationError({
                self.username_field: 'Email or username is required.'
            })

        attrs = attrs.copy()
        attrs[self.username_field] = self._resolve_login_email(login_value, attrs.get('password'))
        data = super().validate(attrs)

        # Block branch users if branch is not approved/suspended
        role = getattr(self.user, "role", None)
        branch = getattr(self.user, "branch", None)
        if role in {"ADMIN", "SECURITY_INCHARGE", "SECURITY_GUARD"} and branch is not None:
            branch_status = getattr(branch, "status", None)
            if branch_status != "APPROVED":
                raise serializers.ValidationError("Branch is not approved. Please contact Super Admin.")
        
        # Add user data to response
        data['user'] = {
            'id': str(self.user.id),
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'branch_id': str(self.user.branch.id) if getattr(self.user, "branch", None) else None,
            'branch_name': getattr(self.user.branch, "branch_name", None) if getattr(self.user, "branch", None) else None,
            'branch_admin_name': getattr(self.user.branch, "admin_name", None) if getattr(self.user, "branch", None) else None,
            'branch_admin_email': getattr(self.user.branch, "admin_email", None) if getattr(self.user, "branch", None) else None,
            'branch_admin_phone': getattr(self.user.branch, "admin_phone", None) if getattr(self.user, "branch", None) else None,
            'company_name': (
                self.user.branch.tenant.company_name
                if getattr(self.user, "branch", None) and getattr(self.user.branch, "tenant", None)
                else None
            ),
            'company_address': (
                self.user.branch.tenant.company_address
                if getattr(self.user, "branch", None) and getattr(self.user.branch, "tenant", None)
                else None
            ),
        }
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate_new_password(self, value):
        validate_password_strength(value)
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    """Forgot password serializer - Admin only"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate that email exists and belongs to an admin"""
        value = normalize_email(value)
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(NON_ADMIN_FORGOT_PASSWORD_MESSAGE)
        if user.role != 'ADMIN':
            raise serializers.ValidationError(NON_ADMIN_FORGOT_PASSWORD_MESSAGE)
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password serializer"""
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return attrs
    
    def validate_new_password(self, value):
        validate_password_strength(value)
        return value
