"""
URL configuration for tracking app
"""
from django.urls import path
from .views import TrackingIngestView

urlpatterns = [
    path('ingest/', TrackingIngestView.as_view(), name='tracking_ingest'),
]
