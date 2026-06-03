"""
URL configuration for alerts app
"""
from django.urls import path
from .views import (
    AlertListCreateView,
    AlertDetailView,
    AlertAcknowledgeView,
    ActiveAlertsView,
    RecentAlertsView,
    AlertDeleteView
)

urlpatterns = [
    path('', AlertListCreateView.as_view(), name='alert_list_create'),
    path('<str:pk>/', AlertDetailView.as_view(), name='alert_detail'),  # Changed to str for MongoDB ObjectId
    path('<str:pk>/acknowledge/', AlertAcknowledgeView.as_view(), name='alert_acknowledge'),
    path('<str:pk>/delete/', AlertDeleteView.as_view(), name='alert_delete'),
    path('active/', ActiveAlertsView.as_view(), name='active_alerts'),
    path('recent/', RecentAlertsView.as_view(), name='recent_alerts'),
]

