"""
AI Engine API URLs
"""
from django.urls import path
from .views import (
    AnalyzeFrameView,
    ProcessCameraView,
    FullPipelineView,
    ModelInfoView,
    HealthCheckView,
    StartContinuousMonitorView,
    StopContinuousMonitorView,
    MonitorStatusView,
    realtime_tracking_sse_view,
    StopTrackingView,
)

urlpatterns = [
    # Main endpoints
    path('analyze-frame/', AnalyzeFrameView.as_view(), name='ai-analyze-frame'),
    path('process-camera/', ProcessCameraView.as_view(), name='ai-process-camera'),
    path('full-pipeline/', FullPipelineView.as_view(), name='ai-full-pipeline'),

    # Continuous monitoring
    path('monitor/start/', StartContinuousMonitorView.as_view(), name='ai-monitor-start'),
    path('monitor/stop/', StopContinuousMonitorView.as_view(), name='ai-monitor-stop'),
    path('monitor/status/', MonitorStatusView.as_view(), name='ai-monitor-status'),

    # Real-time tracking overlay via Server-Sent Events (canvas bounding boxes).
    # Plain Django view — NOT APIView — so DRF content negotiation never rejects
    # the browser's "Accept: text/event-stream" header with a 406.
    path('cameras/<pk>/realtime-tracking/', realtime_tracking_sse_view, name='ai-realtime-tracking'),

    # Info and monitoring
    path('model-info/', ModelInfoView.as_view(), name='ai-model-info'),
    path('health/', HealthCheckView.as_view(), name='ai-health'),
    
    # Entity-Driven Tracking
    path('suspects/<global_id>/stop-tracking/', StopTrackingView.as_view(), name='ai-stop-tracking'),
]

