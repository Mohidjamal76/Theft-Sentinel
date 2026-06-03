"""
Dashboard Views - Stats and Analytics APIs

RBAC Rules for Reports/Dashboard:
----------------------------------
- Admin: Generate manual reports, View automatic and old reports, Delete reports
- Security In-Charge: Generate manual reports, View reports, Cannot delete reports
- Security Guard: Cannot access reports/dashboard
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from django.http import HttpResponse
from datetime import timedelta, datetime
import csv
import io
from calendar import monthrange

from apps.cameras.models import Camera
from apps.alerts.models import Alert
from apps.incidents.models import Incident
from apps.surveillance.models import SurveillanceEvent
from apps.personnel.models import Personnel
from django.contrib.auth import get_user_model
from apps.accounts.permissions import CanViewReports, CanGenerateReports

User = get_user_model()


class DashboardOverviewView(views.APIView):
    """
    Get overall dashboard statistics
    
    Permissions:
    - Admin & Security In-Charge: Can view dashboard/reports
    - Security Guard: Cannot view dashboard/reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """
        Get dashboard overview stats
        """
        user_branch = getattr(request.user, "branch", None)
        scoped = getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None

        # Time ranges
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        cameras_qs = Camera.objects.all()
        if scoped:
            cameras_qs = cameras_qs.filter(branch=user_branch)

        # Camera stats
        total_cameras = cameras_qs.count()
        online_cameras = cameras_qs.filter(status='ONLINE').count()
        offline_cameras = cameras_qs.filter(status='OFFLINE').count()
        
        alerts_qs = Alert.objects.all()
        if scoped:
            alerts_qs = alerts_qs.filter(camera_id__branch=user_branch)

        # Alert stats
        total_alerts = alerts_qs.count()
        active_alerts = alerts_qs.filter(status='ACTIVE').count()
        alerts_today = alerts_qs.filter(timestamp__gte=today_start).count()
        alerts_this_week = alerts_qs.filter(timestamp__gte=week_ago).count()
        
        # Alert severity breakdown
        alerts_by_severity = alerts_qs.values('severity').annotate(count=Count('id'))
        severity_breakdown = {item['severity']: item['count'] for item in alerts_by_severity}
        
        incidents_qs = Incident.objects.all()
        if scoped:
            incidents_qs = incidents_qs.filter(alert_id__camera_id__branch=user_branch)

        # Incident stats
        total_incidents = incidents_qs.count()
        active_incidents = incidents_qs.exclude(status='RESOLVED').count()
        resolved_incidents = incidents_qs.filter(status='RESOLVED').count()
        incidents_today = incidents_qs.filter(created_at__gte=today_start).count()
        
        # Incident status breakdown
        incidents_by_status = incidents_qs.values('status').annotate(count=Count('id'))
        status_breakdown = {item['status']: item['count'] for item in incidents_by_status}
        
        # Personnel stats
        personnel_qs = Personnel.objects.all()
        users_qs = User.objects.filter(is_active=True)
        if scoped:
            personnel_qs = personnel_qs.filter(user__branch=user_branch)
            users_qs = users_qs.filter(branch=user_branch)

        total_personnel = personnel_qs.count()
        total_users = users_qs.count()
        
        # Surveillance events
        events_qs = SurveillanceEvent.objects.all()
        if scoped:
            events_qs = events_qs.filter(camera_id__branch=user_branch)
        events_today = events_qs.filter(created_at__gte=today_start).count()
        events_this_week = events_qs.filter(created_at__gte=week_ago).count()
        
        data = {
            'cameras': {
                'total': total_cameras,
                'online': online_cameras,
                'offline': offline_cameras,
                'online_percentage': round((online_cameras / total_cameras * 100) if total_cameras > 0 else 0, 2)
            },
            'alerts': {
                'total': total_alerts,
                'active': active_alerts,
                'today': alerts_today,
                'this_week': alerts_this_week,
                'by_severity': severity_breakdown
            },
            'incidents': {
                'total': total_incidents,
                'active': active_incidents,
                'resolved': resolved_incidents,
                'today': incidents_today,
                'by_status': status_breakdown,
                'resolution_rate': round((resolved_incidents / total_incidents * 100) if total_incidents > 0 else 0, 2)
            },
            'personnel': {
                'total_personnel': total_personnel,
                'total_users': total_users
            },
            'surveillance_events': {
                'today': events_today,
                'this_week': events_this_week
            },
            'timestamp': now
        }
        
        return Response(data, status=status.HTTP_200_OK)


class AlertsStatsView(views.APIView):
    """
    Get detailed alert statistics
    
    Permissions:
    - Admin & Security In-Charge: Can view alert reports
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """Get alert statistics with time-based breakdown"""
        days = int(request.query_params.get('days', 30))
        
        time_threshold = timezone.now() - timedelta(days=days)
        
        # Alerts over time
        alerts = Alert.objects.filter(timestamp__gte=time_threshold)
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            alerts = alerts.filter(camera_id__branch=user_branch)
        
        # By type
        alerts_by_type = alerts.values('alert_type').annotate(count=Count('id')).order_by('-count')
        
        # By severity
        alerts_by_severity = alerts.values('severity').annotate(count=Count('id'))
        
        # By status
        alerts_by_status = alerts.values('status').annotate(count=Count('id'))
        
        # By camera
        alerts_by_camera = alerts.values(
            'camera_id__name', 'camera_id__location'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        
        # Daily trend (last N days)
        daily_counts = []
        for i in range(days):
            day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            count = alerts.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
            daily_counts.append({
                'date': day_start.date().isoformat(),
                'count': count
            })
        
        data = {
            'period_days': days,
            'total_alerts': alerts.count(),
            'by_type': list(alerts_by_type),
            'by_severity': list(alerts_by_severity),
            'by_status': list(alerts_by_status),
            'top_cameras': list(alerts_by_camera),
            'daily_trend': list(reversed(daily_counts))
        }
        
        return Response(data, status=status.HTTP_200_OK)


class IncidentsStatsView(views.APIView):
    """
    Get detailed incident statistics
    
    Permissions:
    - Admin & Security In-Charge: Can view incident reports
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """Get incident statistics"""
        days = int(request.query_params.get('days', 30))
        
        time_threshold = timezone.now() - timedelta(days=days)
        
        incidents = Incident.objects.filter(created_at__gte=time_threshold)
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            incidents = incidents.filter(alert_id__camera_id__branch=user_branch)
        
        # By status
        incidents_by_status = incidents.values('status').annotate(count=Count('id'))
        
        # By assigned user
        incidents_by_user = incidents.filter(
            assigned_to__isnull=False
        ).values(
            'assigned_to__username'
        ).annotate(count=Count('id')).order_by('-count')[:10]
        
        # Average resolution time (for resolved incidents)
        resolved_incidents = incidents.filter(status='RESOLVED')
        
        # Daily trend
        daily_counts = []
        for i in range(days):
            day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            count = incidents.filter(created_at__gte=day_start, created_at__lt=day_end).count()
            daily_counts.append({
                'date': day_start.date().isoformat(),
                'count': count
            })
        
        data = {
            'period_days': days,
            'total_incidents': incidents.count(),
            'resolved': resolved_incidents.count(),
            'by_status': list(incidents_by_status),
            'top_assignees': list(incidents_by_user),
            'daily_trend': list(reversed(daily_counts))
        }
        
        return Response(data, status=status.HTTP_200_OK)


class CamerasStatsView(views.APIView):
    """
    Get camera statistics
    
    Permissions:
    - Admin & Security In-Charge: Can view camera reports
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """Get camera statistics"""
        cameras = Camera.objects.all()
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            cameras = cameras.filter(branch=user_branch)
        
        # By status
        cameras_by_status = cameras.values('status').annotate(count=Count('id'))
        
        # By zone
        cameras_by_zone = cameras.values('zone').annotate(count=Count('id')).order_by('-count')
        
        # Alerts per camera (top 10)
        cameras_with_alerts = cameras.annotate(
            alert_count=Count('alerts')
        ).order_by('-alert_count')[:10]
        
        camera_alert_data = []
        for camera in cameras_with_alerts:
            camera_alert_data.append({
                'camera_id': camera.id,
                'name': camera.name,
                'location': camera.location,
                'zone': camera.zone,
                'alert_count': camera.alert_count
            })
        
        data = {
            'total_cameras': cameras.count(),
            'by_status': list(cameras_by_status),
            'by_zone': list(cameras_by_zone),
            'top_alert_cameras': camera_alert_data
        }
        
        return Response(data, status=status.HTTP_200_OK)


class RecentActivityView(views.APIView):
    """
    Get recent activity feed
    
    Permissions:
    - Admin & Security In-Charge: Can view activity reports
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """Get recent activity across all modules"""
        limit = int(request.query_params.get('limit', 20))

        user_branch = getattr(request.user, "branch", None)
        scoped = getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None
        
        # Recent alerts
        recent_alerts = Alert.objects.select_related('camera_id').order_by('-timestamp')
        if scoped:
            recent_alerts = recent_alerts.filter(camera_id__branch=user_branch)
        recent_alerts = recent_alerts[:limit]
        
        # Recent incidents
        recent_incidents = Incident.objects.select_related('alert_id', 'assigned_to').order_by('-created_at')
        if scoped:
            recent_incidents = recent_incidents.filter(alert_id__camera_id__branch=user_branch)
        recent_incidents = recent_incidents[:limit]
        
        # Recent surveillance events
        recent_events = SurveillanceEvent.objects.select_related('camera_id').order_by('-created_at')
        if scoped:
            recent_events = recent_events.filter(camera_id__branch=user_branch)
        recent_events = recent_events[:limit]
        
        alerts_data = []
        for alert in recent_alerts:
            alerts_data.append({
                'type': 'alert',
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'camera': alert.camera_id.name,
                'location': alert.camera_id.location,
                'status': alert.status,
                'timestamp': alert.timestamp
            })
        
        incidents_data = []
        for incident in recent_incidents:
            incidents_data.append({
                'type': 'incident',
                'id': incident.id,
                'alert_type': incident.alert_id.alert_type,
                'assigned_to': incident.assigned_to.username if incident.assigned_to else None,
                'status': incident.status,
                'timestamp': incident.created_at
            })
        
        events_data = []
        for event in recent_events:
            events_data.append({
                'type': 'surveillance_event',
                'id': event.id,
                'event_type': event.event_type,
                'camera': event.camera_id.name,
                'location': event.camera_id.location,
                'timestamp': event.created_at
            })
        
        # Combine and sort by timestamp
        all_activities = alerts_data + incidents_data + events_data
        all_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        data = {
            'activities': all_activities[:limit]
        }
        
        return Response(data, status=status.HTTP_200_OK)


class RealTimeAnalyticsView(views.APIView):
    """
    Get real-time analytics data for the reporting dashboard
    
    Permissions:
    - Admin & Security In-Charge: Can view real-time analytics
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """
        Get real-time analytics including active alerts, system health, and camera status.
        
        System health is derived from actual camera feed state (feed-driven status).
        Health classification:
        - EXCELLENT: 100% cameras online
        - GOOD: ≥75% cameras online
        - DEGRADED: ≥50% cameras online
        - CRITICAL: ≥25% cameras online
        - POOR: <25% cameras online
        
        OPTIMIZED: Uses cached camera status (updated by periodic feed checker every 5 seconds).
        """
        now = timezone.now()

        user_branch = getattr(request.user, "branch", None)
        scoped = getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None
        
        # Active alerts count
        active_alerts_qs = Alert.objects.filter(status='ACTIVE')
        if scoped:
            active_alerts_qs = active_alerts_qs.filter(camera_id__branch=user_branch)
        active_alerts = active_alerts_qs.count()
        
        # System health calculation based on feed-driven camera status
        # Status is updated by periodic feed checks (every 5 seconds via management command)
        cameras_qs = Camera.objects.all()
        if scoped:
            cameras_qs = cameras_qs.filter(branch=user_branch)
        total_cameras = cameras_qs.count()
        online_cameras = cameras_qs.filter(status='ONLINE').count()
        offline_cameras = total_cameras - online_cameras
        
        # Classify system health based on online camera ratio (5-level system)
        if total_cameras == 0:
            health_status = 'POOR'
            health_message = 'No cameras configured'
            online_ratio = 0.0
        else:
            online_ratio = online_cameras / total_cameras
            
            if online_ratio >= 1.0:
                health_status = 'EXCELLENT'
                health_message = f'All {total_cameras} cameras online'
            elif online_ratio >= 0.75:
                health_status = 'GOOD'
                health_message = f'{online_cameras}/{total_cameras} cameras online'
            elif online_ratio >= 0.50:
                health_status = 'DEGRADED'
                health_message = f'{online_cameras}/{total_cameras} cameras online - Degraded'
            elif online_ratio >= 0.25:
                health_status = 'CRITICAL'
                health_message = f'{online_cameras}/{total_cameras} cameras online - Critical'
            else:
                health_status = 'POOR'
                health_message = f'{online_cameras}/{total_cameras} cameras online - Poor'
        
        # Camera feeds status (feed-driven) - optimized query
        # Status is updated by periodic feed checker (every 5 seconds via management command)
        # This view simply reads the current status - no status modification here
        cameras = Camera.objects.only('id', 'name', 'location', 'zone', 'status', 'last_feed_timestamp').all()
        if scoped:
            cameras = cameras.filter(branch=user_branch)
        camera_feeds = []
        for camera in cameras:
            camera_feeds.append({
                'id': str(camera.id),
                'name': camera.name,
                'location': camera.location,
                'zone': camera.zone,
                'status': camera.status,
                'is_online': camera.status == 'ONLINE',
                'last_feed_timestamp': camera.last_feed_timestamp.isoformat() if hasattr(camera, 'last_feed_timestamp') and camera.last_feed_timestamp else None
            })
        
        data = {
            'active_alerts': active_alerts,
            'system_health': {
                'status': health_status,
                'message': health_message,
                'online_cameras': online_cameras,
                'offline_cameras': offline_cameras,
                'total_cameras': total_cameras,
                'online_ratio': round(online_ratio, 2)
            },
            'camera_feeds': camera_feeds,
            'timestamp': now
        }
        
        return Response(data, status=status.HTTP_200_OK)


class HistoricalAlertReportingView(views.APIView):
    """
    Get historical alert data aggregated by day, week, or month
    
    Uses ONLY alerts from Alert model (generated by cameras and AI models).
    Does NOT include incidents.
    
    Permissions:
    - Admin & Security In-Charge: Can view historical reports
    - Security Guard: Cannot view reports
    """
    permission_classes = [IsAuthenticated, CanViewReports]
    
    def get(self, request):
        """Get historical alert data with aggregation"""
        period = request.query_params.get('period', 'daily')  # daily, weekly, monthly
        days = int(request.query_params.get('days', 30))
        
        now = timezone.now()
        start_date = now - timedelta(days=days)
        
        # Get all alerts in the period (ONLY alerts, not incidents)
        # Alerts come from cameras and AI models
        alerts = Alert.objects.filter(timestamp__gte=start_date).select_related('camera_id')
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            alerts = alerts.filter(camera_id__branch=user_branch)
        
        # Aggregate based on period
        if period == 'daily':
            data = self._get_daily_aggregation(alerts, days, now)
        elif period == 'weekly':
            data = self._get_weekly_aggregation(alerts, days, now)
        elif period == 'monthly':
            data = self._get_monthly_aggregation(alerts, days, now)
        else:
            data = self._get_daily_aggregation(alerts, days, now)
        
        # Add summary statistics
        data['summary'] = {
            'total_alerts': alerts.count(),
            'active': alerts.filter(status='ACTIVE').count(),
            'acknowledged': alerts.filter(status='ACKED').count(),
            'resolved': alerts.filter(status__in=['ACKED', 'RESOLVED']).count(),
            'period': period,
            'days_covered': days
        }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def _get_daily_aggregation(self, alerts, days, now):
        """Aggregate alerts by day"""
        daily_counts = []
        for i in range(days):
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            day_alerts = alerts.filter(timestamp__gte=day_start, timestamp__lt=day_end)
            
            daily_counts.append({
                'date': day_start.date().isoformat(),
                'count': day_alerts.count(),
                'active': day_alerts.filter(status='ACTIVE').count(),
                'resolved': day_alerts.filter(status__in=['ACKED', 'RESOLVED']).count()
            })
        
        return {
            'data': list(reversed(daily_counts)),
            'trend': self._calculate_trend(daily_counts)
        }
    
    def _get_weekly_aggregation(self, alerts, days, now):
        """Aggregate alerts by week"""
        weekly_counts = []
        weeks = (days // 7) + (1 if days % 7 > 0 else 0)
        
        for i in range(weeks):
            week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=i+1)
            week_end = week_start + timedelta(weeks=1)
            week_alerts = alerts.filter(timestamp__gte=week_start, timestamp__lt=week_end)
            
            weekly_counts.append({
                'week_start': week_start.date().isoformat(),
                'week_end': (week_end - timedelta(days=1)).date().isoformat(),
                'count': week_alerts.count(),
                'active': week_alerts.filter(status='ACTIVE').count(),
                'resolved': week_alerts.filter(status__in=['ACKED', 'RESOLVED']).count()
            })
        
        return {
            'data': list(reversed(weekly_counts)),
            'trend': self._calculate_trend(weekly_counts)
        }
    
    def _get_monthly_aggregation(self, alerts, days, now):
        """Aggregate alerts by month"""
        monthly_counts = []
        months = (days // 30) + (1 if days % 30 > 0 else 0)
        
        for i in range(months):
            # Calculate month start
            if i == 0:
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                # Go back i months
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                for _ in range(i):
                    # Get previous month
                    if month_start.month == 1:
                        month_start = month_start.replace(year=month_start.year - 1, month=12)
                    else:
                        month_start = month_start.replace(month=month_start.month - 1)
            
            # Calculate month end
            days_in_month = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start + timedelta(days=days_in_month)
            
            month_alerts = alerts.filter(timestamp__gte=month_start, timestamp__lt=month_end)
            
            monthly_counts.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'count': month_alerts.count(),
                'active': month_alerts.filter(status='ACTIVE').count(),
                'resolved': month_alerts.filter(status__in=['ACKED', 'RESOLVED']).count()
            })
        
        return {
            'data': list(reversed(monthly_counts)),
            'trend': self._calculate_trend(monthly_counts)
        }
    
    def _calculate_trend(self, data_points):
        """Calculate trend (increasing, decreasing, stable)"""
        if len(data_points) < 2:
            return 'stable'
        
        counts = [point['count'] for point in data_points]
        first_half = sum(counts[:len(counts)//2]) / (len(counts)//2) if len(counts)//2 > 0 else 0
        second_half = sum(counts[len(counts)//2:]) / (len(counts) - len(counts)//2) if (len(counts) - len(counts)//2) > 0 else 0
        
        if second_half > first_half * 1.1:
            return 'increasing'
        elif second_half < first_half * 0.9:
            return 'decreasing'
        else:
            return 'stable'


class IncidentReportExportView(views.APIView):
    """
    Export incident reports as CSV or PDF
    
    Permissions:
    - Admin & Security In-Charge: Can export reports
    - Security Guard: Cannot export reports
    """
    permission_classes = [IsAuthenticated, CanGenerateReports]
    
    def get(self, request):
        """Export incident reports"""
        export_format = request.query_params.get('format', 'csv')  # csv or pdf
        days = int(request.query_params.get('days', 30))
        period = request.query_params.get('period', 'daily')
        
        now = timezone.now()
        start_date = now - timedelta(days=days)
        incidents = Incident.objects.filter(created_at__gte=start_date).select_related(
            'alert_id', 'alert_id__camera_id', 'assigned_to'
        )
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            incidents = incidents.filter(alert_id__camera_id__branch=user_branch)
        
        if export_format == 'csv':
            return self._export_csv(incidents, period, days, now)
        elif export_format == 'pdf':
            return self._export_pdf(incidents, period, days, now)
        else:
            return Response(
                {'error': 'Invalid format. Use "csv" or "pdf"'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _export_csv(self, incidents, period, days, now):
        """Export incidents as CSV"""
        response = HttpResponse(content_type='text/csv')
        filename = f'incident_report_{period}_{days}days_{now.strftime("%Y%m%d")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Incident ID', 'Alert Type', 'Camera', 'Location', 'Zone',
            'Status', 'Assigned To', 'Created At', 'Updated At', 'Notes'
        ])
        
        # Write data
        for incident in incidents:
            alert = incident.alert_id
            camera = alert.camera_id if alert else None
            
            writer.writerow([
                str(incident.id),
                alert.alert_type if alert else 'N/A',
                camera.name if camera else 'N/A',
                camera.location if camera else 'N/A',
                camera.zone if camera else 'N/A',
                incident.status,
                incident.assigned_to.username if incident.assigned_to else 'Unassigned',
                incident.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                incident.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                incident.notes[:100] if incident.notes else ''  # Truncate long notes
            ])
        
        return response
    
    def _export_pdf(self, incidents, period, days, now):
        """Export incidents as PDF"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            # If reportlab is not installed, return error
            return Response(
                {'error': 'PDF export requires reportlab library. Please install it: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        filename = f'incident_report_{period}_{days}days_{now.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1B3C53'),
            spaceAfter=30
        )
        elements.append(Paragraph('Theft Sentinel - Incident Report', title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary
        summary_data = [
            ['Report Period', f'Last {days} days'],
            ['Period Type', period.title()],
            ['Total Incidents', str(incidents.count())],
            ['Resolved', str(incidents.filter(status='RESOLVED').count())],
            ['Active', str(incidents.exclude(status='RESOLVED').count())],
            ['Generated At', now.strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#234C6A')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Incident details table
        if incidents.exists():
            table_data = [['ID', 'Alert Type', 'Camera', 'Status', 'Assigned To', 'Created At']]
            
            for incident in incidents[:100]:  # Limit to 100 rows for PDF
                alert = incident.alert_id
                camera = alert.camera_id if alert else None
                
                table_data.append([
                    str(incident.id)[:8] + '...',  # Truncate ID
                    alert.alert_type[:20] if alert else 'N/A',
                    camera.name[:20] if camera else 'N/A',
                    incident.status,
                    incident.assigned_to.username[:15] if incident.assigned_to else 'Unassigned',
                    incident.created_at.strftime('%Y-%m-%d')
                ])
            
            incident_table = Table(table_data, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch])
            incident_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B3C53')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(incident_table)
            
            if incidents.count() > 100:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph(
                    f'Note: Showing first 100 of {incidents.count()} incidents',
                    styles['Normal']
                ))
        
        # Build PDF
        doc.build(elements)
        return response


class AlertReportExportView(views.APIView):
    """
    Export alert reports as CSV or PDF
    
    Uses alerts from Alert model (generated by AI camera models)
    
    Permissions:
    - Admin & Security In-Charge: Can export reports
    - Security Guard: Cannot export reports
    """
    permission_classes = [IsAuthenticated, CanGenerateReports]
    
    def get(self, request):
        """
        Export alert reports as CSV or PDF.
        
        Query Parameters:
        - export_type: 'csv' or 'pdf' (required)
        - days: Number of days to include (default: 30)
        - period: 'daily', 'weekly', or 'monthly' (default: 'daily')
        
        Note: We use 'export_type' instead of 'format' to avoid DRF's format
        negotiation, which would intercept ?format=csv/pdf and return 404
        if CSV/PDF renderers aren't configured.
        """
        # Use 'export_type' instead of 'format' to avoid DRF format negotiation
        export_type = request.query_params.get('export_type', request.query_params.get('format', 'csv')).lower()
        days = int(request.query_params.get('days', 30))
        period = request.query_params.get('period', 'daily')
        
        # Validate export_type
        if export_type not in ['csv', 'pdf']:
            return Response(
                {'error': 'Invalid export_type. Use "csv" or "pdf"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        now = timezone.now()
        start_date = now - timedelta(days=days)
        alerts = Alert.objects.filter(timestamp__gte=start_date).select_related('camera_id')
        user_branch = getattr(request.user, "branch", None)
        if getattr(request.user, "role", None) != "SUPER_ADMIN" and user_branch is not None:
            alerts = alerts.filter(camera_id__branch=user_branch)
        
        if export_type == 'csv':
            return self._export_csv(alerts, period, days, now)
        elif export_type == 'pdf':
            return self._export_pdf(alerts, period, days, now)
    
    def _export_csv(self, alerts, period, days, now):
        """Export alerts as CSV"""
        response = HttpResponse(content_type='text/csv')
        filename = f'alert_report_{period}_{days}days_{now.strftime("%Y%m%d")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Alert ID', 'Alert Type', 'Severity', 'Status', 'Camera Name', 'Location', 'Timestamp'
        ])
        
        # Write data
        for alert in alerts:
            camera = alert.camera_id
            writer.writerow([
                str(alert.id),
                alert.alert_type,
                alert.severity,
                alert.status,
                camera.name if camera else 'N/A',
                camera.location if camera else 'N/A',
                alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    def _export_pdf(self, alerts, period, days, now):
        """Export alerts as PDF"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
        except ImportError:
            # If reportlab is not installed, return error
            return Response(
                {'error': 'PDF export requires reportlab library. Please install it: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        filename = f'alert_report_{period}_{days}days_{now.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1B3C53'),
            spaceAfter=30
        )
        elements.append(Paragraph('Theft Sentinel – Historical Alert Report', title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary statistics
        total_alerts = alerts.count()
        active_alerts = alerts.filter(status='ACTIVE').count()
        resolved_alerts = alerts.filter(status__in=['ACKED', 'RESOLVED']).count()
        
        summary_data = [
            ['Report Period', f'Last {days} days'],
            ['Period Type', period.title()],
            ['Total Alerts', str(total_alerts)],
            ['Active Alerts', str(active_alerts)],
            ['Resolved Alerts', str(resolved_alerts)],
            ['Generated At', now.strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#234C6A')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Alert details table
        if alerts.exists():
            table_data = [['Alert ID', 'Alert Type', 'Severity', 'Status', 'Camera', 'Location', 'Timestamp']]
            
            for alert in alerts[:100]:  # Limit to 100 rows for PDF
                camera = alert.camera_id
                table_data.append([
                    str(alert.id)[:8] + '...',  # Truncate ID
                    alert.alert_type[:20],
                    alert.severity,
                    alert.status,
                    camera.name[:20] if camera else 'N/A',
                    camera.location[:20] if camera else 'N/A',
                    alert.timestamp.strftime('%Y-%m-%d %H:%M')
                ])
            
            alert_table = Table(table_data, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch, 1*inch])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B3C53')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(alert_table)
            
            if alerts.count() > 100:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph(
                    f'Note: Showing first 100 of {alerts.count()} alerts',
                    styles['Normal']
                ))
        
        # Build PDF
        doc.build(elements)
        return response
