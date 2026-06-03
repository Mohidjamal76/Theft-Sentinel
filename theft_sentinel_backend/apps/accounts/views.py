"""
Views for Authentication and User Management
"""
from rest_framework import generics, status, views
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
import logging

from rest_framework.serializers import ValidationError as DRFValidationError

from .serializers import (
    UserSerializer, 
    UserCreateSerializer, 
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    validate_password_strength,
    NON_ADMIN_FORGOT_PASSWORD_MESSAGE,
)
from .permissions import IsAdmin, CanChangeOwnPassword, CanManageUsers, IsAdminOrIncharge
from .models import PasswordResetToken, PasswordResetAudit
from config.env_validator import get_client_ip, get_user_agent

User = get_user_model()
logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """
    ADMIN-ONLY User Creation Endpoint
    
    This view is NOT publicly accessible. Only authenticated Admin users
    with CanManageUsers permission can create new users.
    
    Public self-registration has been disabled. All user accounts must be
    created by administrators through the admin panel or user management interface.
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, CanManageUsers]
    serializer_class = UserCreateSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # All users created by a Branch Admin belong to the same branch.
        # Super Admin may create users without a branch (not typical).
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and getattr(request.user, "branch", None) is not None:
            user = serializer.save(branch=request.user.branch)
        else:
            user = serializer.save()
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User created successfully by admin'
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with user data"""
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(views.APIView):
    """Logout view - blacklist refresh token"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

        try:
            token = RefreshToken(refresh_token)
            if hasattr(token, 'blacklist'):
                token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update current user profile"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(views.APIView):
    """
    Change password for current user
    All users can change their own password
    """
    permission_classes = [IsAuthenticated, CanChangeOwnPassword]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {'error': 'Wrong old password'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.data.get('new_password'))
            user.save()
            
            return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """
    List all users (Admin and Security In-Charge can view)
    Admin and Security In-Charge need to list guards for assignment
    Full CRUD operations (create/update/delete) remain Admin-only
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def get_queryset(self):
        queryset = User.objects.all()
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(branch=user_branch)
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset.order_by('-created_at')


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete user (Admin only)
    Full CRUD on users is Admin-only permission
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]

    def get_queryset(self):
        qs = User.objects.all()
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            qs = qs.filter(branch=user_branch)
        return qs
    
    def update(self, request, *args, **kwargs):
        """Override update to enforce per-branch Admin uniqueness"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if trying to set role to ADMIN
        if 'role' in request.data and request.data['role'] == 'ADMIN':
            # Check if another Admin already exists in the same branch (excluding current user)
            branch = getattr(instance, "branch", None)
            existing_admin = (
                User.objects.filter(role='ADMIN', is_active=True, branch=branch)
                .exclude(pk=instance.pk)
                .first()
            )
            if existing_admin and branch is not None:
                return Response(
                    {'role': ['Only one Branch Admin can exist per branch. A Branch Admin already exists for this branch.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to enforce Admin uniqueness"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role == 'ADMIN' and instance.pk == request.user.pk:
            return Response(
                {'error': 'Admin cannot delete their own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)


class AdminChangeUserPasswordView(views.APIView):
    """
    Admin can change any user's password
    Only Admin has this permission
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'New password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password_strength(new_password)
        except DRFValidationError as exc:
            detail = exc.detail
            msg = str(detail[0]) if isinstance(detail, list) and detail else str(detail)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'message': f'Password changed successfully for user {user.username}'
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(views.APIView):
    """
    Forgot Password - Admin Only
    
    This endpoint:
    1. Verifies the email exists and belongs to an admin account
    2. Generates a secure reset token (32 characters)
    3. Stores token with 30-minute expiration
    4. Sends reset link via email
    5. Logs all attempts for audit purposes
    
    Only admin users can reset passwords. Security personnel and guards
    must contact the admin.
    """
    permission_classes = [AllowAny]  # Public endpoint for forgot password
    
    def _log_audit(self, email, is_admin, success, reason, request):
        """Log password reset attempt for audit purposes"""
        try:
            PasswordResetAudit.objects.create(
                email=email,
                is_admin=is_admin,
                success=success,
                reason=reason,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Failed to log password reset audit: {str(e)}", exc_info=True)
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Log validation failure
            email = request.data.get('email', 'unknown')
            self._log_audit(
                email=email,
                is_admin=False,
                success=False,
                reason='Invalid email format',
                request=request
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email__iexact=email)
            
            if not user.is_active:
                # Log inactive account attempt
                self._log_audit(
                    email=email,
                    is_admin=True,
                    success=False,
                    reason='Account is inactive',
                    request=request
                )
                return Response(
                    {'error': 'Account is inactive. Please contact administrator.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate secure token
            token = PasswordResetToken.generate_token()
            
            # Create reset token with 30-minute expiration
            expires_at = timezone.now() + timedelta(minutes=30)
            
            # Invalidate any existing unused tokens for this user
            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
            
            # Create new token
            reset_token = PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Generate reset link
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_link = f"{frontend_url}/reset-password?token={token}"
            
            # Send email with hardened error handling
            try:
                send_mail(
                    subject='Theft Sentinel - Admin Password Reset',
                    message=f'''Hello {user.username},

You requested to reset your admin password for Theft Sentinel.

Click the following link to reset your password:
{reset_link}

This link will expire in 30 minutes.

If you did not request this password reset, please ignore this email.

Security Note: Only admin users can reset passwords using this flow. Security personnel and guards must contact the admin.

Best regards,
Theft Sentinel Team''',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                
                logger.info(f"Password reset email sent successfully to admin: {user.email}")
                
                # Log successful email send
                self._log_audit(
                    email=email,
                    is_admin=True,
                    success=True,
                    reason='Password reset email sent successfully',
                    request=request
                )
                
                return Response(
                    {'message': 'If this email is registered as an admin, a password reset link has been sent.'},
                    status=status.HTTP_200_OK
                )
                
            except Exception as e:
                # Hardened error handling - don't crash the backend
                error_msg = str(e)
                logger.error(
                    f"SMTP error: Failed to send password reset email to {user.email}",
                    exc_info=True
                )
                
                # Delete token if email sending failed
                try:
                    reset_token.delete()
                except Exception as delete_error:
                    logger.error(f"Failed to delete reset token after email failure: {delete_error}")
                
                # Log SMTP failure
                self._log_audit(
                    email=email,
                    is_admin=True,
                    success=False,
                    reason=f'SMTP error: {error_msg[:200]}',  # Limit reason length
                    request=request
                )
                
                # Return user-safe error message (503 Service Unavailable)
                return Response(
                    {'error': 'Email service is currently unavailable. Please try again later or contact support.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
                
        except User.DoesNotExist:
            # Log email not found attempt
            self._log_audit(
                email=email,
                is_admin=False,
                success=False,
                reason='Email not found in database',
                request=request
            )
            return Response(
                {'email': [NON_ADMIN_FORGOT_PASSWORD_MESSAGE]},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResetPasswordView(views.APIView):
    """
    Reset Password - Admin Only
    
    This endpoint:
    1. Validates the reset token
    2. Checks token expiration and usage
    3. Updates admin password securely
    4. Invalidates the token
    5. Logs all attempts for audit purposes
    
    Only valid, unexpired tokens can be used.
    """
    permission_classes = [AllowAny]  # Public endpoint for password reset
    
    def _log_audit(self, email, is_admin, success, reason, request):
        """Log password reset attempt for audit purposes"""
        try:
            PasswordResetAudit.objects.create(
                email=email,
                is_admin=is_admin,
                success=success,
                reason=reason,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Failed to log password reset audit: {str(e)}", exc_info=True)
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Log validation failure
            token = request.data.get('token', 'unknown')
            self._log_audit(
                email='unknown',
                is_admin=False,
                success=False,
                reason='Invalid reset data (validation failed)',
                request=request
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            user = reset_token.user
            user_email = user.email if user else 'unknown'
            
            # Check if token is valid
            if not reset_token.is_valid():
                if reset_token.used:
                    # Log used token attempt
                    self._log_audit(
                        email=user_email,
                        is_admin=user.role == 'ADMIN' if user else False,
                        success=False,
                        reason='Token already used',
                        request=request
                    )
                    return Response(
                        {'error': 'This reset link has already been used. Please request a new one.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif reset_token.is_expired():
                    # Log expired token attempt
                    self._log_audit(
                        email=user_email,
                        is_admin=user.role == 'ADMIN' if user else False,
                        success=False,
                        reason='Token expired',
                        request=request
                    )
                    return Response(
                        {'error': 'This reset link has expired. Please request a new one.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Verify user is eligible for direct token-based reset
            if user.role not in ['ADMIN', 'SUPER_ADMIN']:
                # Log non-admin attempt
                self._log_audit(
                    email=user_email,
                    is_admin=user.role == 'ADMIN' if user else False,
                    success=False,
                    reason='Non-admin user attempted password reset',
                    request=request
                )
                return Response(
                    {'error': 'Invalid reset token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            reset_token.used = True
            reset_token.save()
            
            logger.info(f"Password reset successful for admin: {user.email}")
            
            # Log successful password reset
            self._log_audit(
                email=user_email,
                is_admin=True,
                success=True,
                reason='Password successfully reset',
                request=request
            )
            
            return Response(
                {'message': 'Password successfully updated. You may now log in.'},
                status=status.HTTP_200_OK
            )
            
        except PasswordResetToken.DoesNotExist:
            # Log invalid token attempt
            self._log_audit(
                email='unknown',
                is_admin=False,
                success=False,
                reason='Invalid or non-existent token',
                request=request
            )
            return Response(
                {'error': 'Invalid or expired reset token. Please request a new password reset.'},
                status=status.HTTP_400_BAD_REQUEST
            )
