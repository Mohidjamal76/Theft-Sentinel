"""
Mobile/Notification Views

RBAC Rules:
-----------
- Admin: Can view all notifications, send notifications
- Security In-Charge: Can view own notifications, send notifications (for reports)
- Security Guard: Can view own notifications only
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from .models import Notification
from .serializers import (
    NotificationSerializer,
    SendSMSSerializer,
    SendEmailSerializer,
    BulkNotificationSerializer
)
from .services import NotificationService
from apps.accounts.permissions import IsAdminOrIncharge

User = get_user_model()


class NotificationListView(generics.ListAPIView):
    """
    List all notifications
    
    Permissions:
    - Admin: Can view all notifications
    - Security In-Charge & Security Guard: Can view only their own notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.select_related('user').all()
        
        # Admin: Can view all notifications
        if self.request.user.role == 'ADMIN':
            pass  # No filtering
        else:
            # Security In-Charge & Security Guard: Only view their own notifications
            queryset = queryset.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by type
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(notification_type=type_filter)
        
        return queryset.order_by('-created_at')


class MyNotificationsView(generics.ListAPIView):
    """
    Get current user's notifications
    
    Permissions:
    - All authenticated users can view their own notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class SendSMSView(views.APIView):
    """
    Send SMS notification
    
    Permissions:
    - Admin & Security In-Charge: Can send SMS notifications
    - Security Guard: Cannot send SMS notifications
    """
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def post(self, request):
        serializer = SendSMSSerializer(data=request.data)
        
        if serializer.is_valid():
            success = NotificationService.send_sms(
                user=request.user,
                phone_number=serializer.validated_data['phone_number'],
                message=serializer.validated_data['message']
            )
            
            if success:
                return Response({
                    'message': 'SMS sent successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send SMS'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendEmailView(views.APIView):
    """
    Send Email notification
    
    Permissions:
    - Admin & Security In-Charge: Can send email notifications
    - Security Guard: Cannot send email notifications
    """
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def post(self, request):
        serializer = SendEmailSerializer(data=request.data)
        
        if serializer.is_valid():
            success = NotificationService.send_email(
                user=request.user,
                email_address=serializer.validated_data['email_address'],
                subject=serializer.validated_data['subject'],
                message=serializer.validated_data['message']
            )
            
            if success:
                return Response({
                    'message': 'Email sent successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send email'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkNotificationView(views.APIView):
    """
    Send bulk notifications to multiple users
    
    Permissions:
    - Admin & Security In-Charge: Can send bulk notifications
    - Security Guard: Cannot send bulk notifications
    """
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def post(self, request):
        serializer = BulkNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            user_ids = serializer.validated_data['user_ids']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            send_sms = serializer.validated_data.get('send_sms', False)
            send_email = serializer.validated_data.get('send_email', True)
            
            users = User.objects.filter(id__in=user_ids)
            
            results = {
                'email_sent': 0,
                'email_failed': 0,
                'sms_sent': 0,
                'sms_failed': 0
            }
            
            for user in users:
                # Send email
                if send_email and user.email:
                    success = NotificationService.send_email(
                        user=user,
                        email_address=user.email,
                        subject=subject,
                        message=message
                    )
                    if success:
                        results['email_sent'] += 1
                    else:
                        results['email_failed'] += 1
                
                # Send SMS
                if send_sms:
                    try:
                        personnel = user.personnel_profile
                        if personnel.phone:
                            success = NotificationService.send_sms(
                                user=user,
                                phone_number=personnel.phone,
                                message=message
                            )
                            if success:
                                results['sms_sent'] += 1
                            else:
                                results['sms_failed'] += 1
                    except:
                        pass
            
            return Response(results, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
