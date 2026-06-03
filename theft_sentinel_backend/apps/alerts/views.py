"""
Alert Views

RBAC Rules:
-----------
- Admin: View all alerts & alert history, Delete alerts
- Security In-Charge: View all alerts & alert history, Cannot delete alerts
- Security Guard: View real-time alerts only (no history), Cannot delete alerts
"""
from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Alert
from .serializers import AlertSerializer, AlertCreateSerializer, AlertAcknowledgeSerializer
from .serializers import VALID_ALERT_SEVERITIES
from .services import dispatch_theft_alert_notifications
from apps.accounts.permissions import IsAdminOrIncharge, CanViewAlerts, CanDeleteAlerts

logger = logging.getLogger(__name__)


class AlertListCreateView(generics.ListCreateAPIView):
    """
    List all alerts or create new
    
    Permissions:
    - Admin & Security In-Charge: Can view all alerts including history
    - Security Guard: Can view alerts (filtered in queryset)
    - All: Can create alerts (from AI system)
    """
    queryset = Alert.objects.all()
    permission_classes = [IsAuthenticated, CanViewAlerts]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AlertCreateSerializer
        return AlertSerializer
    
    def get_queryset(self):
        queryset = Alert.objects.select_related('camera_id').all()

        # Branch scoping
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(camera_id__branch=user_branch)
        
        # Security Guard: Only view recent alerts (last 24 hours - real-time alerts)
        # Cannot view alert history
        if self.request.user.role == 'SECURITY_GUARD':
            time_threshold = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=time_threshold)
        
        # Admin & Security In-Charge: Can view all alerts including history
        # No filtering needed
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by acknowledged (for backward compatibility with frontend)
        # acknowledged=true -> ACKED or RESOLVED, acknowledged=false -> ACTIVE
        acknowledged_param = self.request.query_params.get('acknowledged', None)
        if acknowledged_param is not None:
            if acknowledged_param.lower() == 'true':
                queryset = queryset.filter(status__in=['ACKED', 'RESOLVED'])
            elif acknowledged_param.lower() == 'false':
                queryset = queryset.filter(status='ACTIVE')
        
        # Filter by camera
        camera_id = self.request.query_params.get('camera_id', None)
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        
        # Filter by alert_type
        alert_type = self.request.query_params.get('alert_type', None)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)

        # Filter by severity (backend supports MEDIUM and HIGH only)
        severity = self.request.query_params.get('severity', None)
        if severity:
            severity = severity.strip().upper()
            if severity not in VALID_ALERT_SEVERITIES:
                raise ValidationError({'severity': ['Severity must be MEDIUM or HIGH.']})
            queryset = queryset.filter(severity__iexact=severity)
        
        # Filter by date range (only for Admin & Security In-Charge)
        if self.request.user.role in ['ADMIN', 'SECURITY_INCHARGE']:
            start_date = self.request.query_params.get('start_date', None)
            if start_date:
                queryset = queryset.filter(timestamp__gte=start_date)
            
            end_date = self.request.query_params.get('end_date', None)
            if end_date:
                queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        alert = serializer.save()
        try:
            dispatch_theft_alert_notifications(alert, async_send=True)
        except Exception:
            logger.exception("Failed to dispatch alert notifications for alert %s", alert.id)


class AlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete alert
    
    Permissions:
    - Admin: Full access (view, update, delete)
    - Security In-Charge: View and update only
    - Security Guard: View only (recent alerts)
    """
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, CanViewAlerts]
    
    def get_queryset(self):
        queryset = Alert.objects.select_related('camera_id').all()

        # Branch scoping
        user_branch = getattr(self.request.user, "branch", None)
        if getattr(self.request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            queryset = queryset.filter(camera_id__branch=user_branch)
        
        # Security Guard: Only view recent alerts (last 24 hours)
        if self.request.user.role == 'SECURITY_GUARD':
            time_threshold = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=time_threshold)
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """
        Only Admin can delete alerts
        """
        if request.user.role != 'ADMIN':
            return Response(
                {'error': 'You do not have permission to delete alerts. Only Admin can delete alerts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Security Guard cannot update alerts
        """
        if request.user.role == 'SECURITY_GUARD':
            return Response(
                {'error': 'You do not have permission to update alerts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Security Guard cannot update alerts
        """
        if request.user.role == 'SECURITY_GUARD':
            return Response(
                {'error': 'You do not have permission to update alerts.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)


class AlertAcknowledgeView(views.APIView):
    """
    Acknowledge or resolve an alert
    
    Permissions:
    - Admin & Security In-Charge: Can acknowledge/resolve alerts
    - Security Guard: Cannot acknowledge/resolve alerts
    
    When guard_id is provided, creates an incident with status ASSIGNED
    """
    permission_classes = [IsAuthenticated, IsAdminOrIncharge]
    
    def patch(self, request, pk):
        from django.contrib.auth import get_user_model
        from apps.incidents.models import Incident
        
        User = get_user_model()
        
        try:
            queryset = Alert.objects.select_related('camera_id').all()
            user_branch = getattr(request.user, "branch", None)
            if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                queryset = queryset.filter(camera_id__branch=user_branch)
            alert = queryset.get(pk=pk)
        except Alert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AlertAcknowledgeSerializer(data=request.data)
        if serializer.is_valid():
            alert.status = serializer.validated_data['status']
            alert.save()
            
            # Guard assignment is mandatory - create incident
            guard_email = serializer.validated_data['guard_email']
            comment = serializer.validated_data.get('comment', '')
            
            try:
                guard_qs = User.objects.filter(email__iexact=guard_email, role='SECURITY_GUARD', is_active=True)
                user_branch = getattr(request.user, "branch", None)
                if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
                    guard_qs = guard_qs.filter(branch=user_branch)
                guard = guard_qs.get()
                # Create incident with status ASSIGNED
                incident = Incident.objects.create(
                    alert_id=alert,
                    assigned_to=guard,
                    assigned_by=request.user,  # Track who assigned the incident
                    status='ASSIGNED',
                    notes=comment
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'Guard not found or invalid guard email'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to create incident: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActiveAlertsView(generics.ListAPIView):
    """
    Get all active alerts
    
    Permissions:
    - All authenticated users can view active alerts
    - Security Guard: Only recent active alerts (last 24 hours)
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, CanViewAlerts]
    
    def get_queryset(self):
        queryset = Alert.objects.select_related('camera_id').filter(
            status='ACTIVE'
        )
        
        # Security Guard: Only view recent alerts (last 24 hours)
        if self.request.user.role == 'SECURITY_GUARD':
            time_threshold = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=time_threshold)
        
        return queryset.order_by('-timestamp')


class RecentAlertsView(generics.ListAPIView):
    """
    Get alerts from the last 24 hours
    
    Permissions:
    - All authenticated users can view recent alerts
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, CanViewAlerts]
    
    def get_queryset(self):
        time_threshold = timezone.now() - timedelta(hours=24)
        return Alert.objects.select_related('camera_id').filter(
            timestamp__gte=time_threshold
        ).order_by('-timestamp')


class AlertDeleteView(views.APIView):
    """
    Delete an alert
    
    Permissions:
    - Only Admin can delete alerts
    """
    permission_classes = [IsAuthenticated, CanDeleteAlerts]
    
    def delete(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk)
        except Alert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        alert.delete()
        return Response(
            {'message': 'Alert deleted successfully'},
            status=status.HTTP_200_OK
        )
