"""
URL configuration for cameras app
"""
from django.urls import path
from .views import (
    CameraListCreateView,
    CameraDetailView,
    CameraStatusUpdateView,
    CamerasByZoneView,
    CameraFeedView,
    CameraStreamURLView
)

urlpatterns = [
    path('', CameraListCreateView.as_view(), name='camera_list_create'),
    path('<str:pk>/', CameraDetailView.as_view(), name='camera_detail'),
    path('<str:pk>/status/', CameraStatusUpdateView.as_view(), name='camera_status_update'),
    path('<str:pk>/stream-url/', CameraStreamURLView.as_view(), name='camera_stream_url'),
    path('<str:pk>/feed/', CameraFeedView.as_view(), name='camera_feed'),
    path('zone/<str:zone>/', CamerasByZoneView.as_view(), name='cameras_by_zone'),
]

