"""
URL configuration for dashboard app
"""
from django.urls import path
from .views import (
    DashboardOverviewView,
    AlertsStatsView,
    IncidentsStatsView,
    CamerasStatsView,
    RecentActivityView,
    RealTimeAnalyticsView,
    HistoricalAlertReportingView,
    AlertReportExportView
)

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='dashboard_overview'),
    path('alerts-stats/', AlertsStatsView.as_view(), name='alerts_stats'),
    path('incidents-stats/', IncidentsStatsView.as_view(), name='incidents_stats'),
    path('cameras-stats/', CamerasStatsView.as_view(), name='cameras_stats'),
    path('recent-activity/', RecentActivityView.as_view(), name='recent_activity'),
    # Historical Data Reporting endpoints (ALERTS ONLY - no incidents)
    path('realtime-analytics/', RealTimeAnalyticsView.as_view(), name='realtime_analytics'),
    path('historical-alerts/', HistoricalAlertReportingView.as_view(), name='historical_alerts'),
    path('export-alerts/', AlertReportExportView.as_view(), name='export_alerts'),
]

