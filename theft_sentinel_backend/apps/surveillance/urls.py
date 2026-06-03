"""
URL configuration for surveillance app
"""
from django.urls import path
from .views import (
    SurveillanceEventListView,
    SurveillanceEventDetailView,
    SurveillanceEventIngestView
)

urlpatterns = [
    path('events/', SurveillanceEventListView.as_view(), name='surveillance_event_list'),
    path('events/<int:pk>/', SurveillanceEventDetailView.as_view(), name='surveillance_event_detail'),
    path('ingest/', SurveillanceEventIngestView.as_view(), name='surveillance_event_ingest'),
]

