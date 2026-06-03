"""
URL configuration for incidents app
"""
from django.urls import path
from .views import (
    IncidentListCreateView,
    IncidentDetailView,
    IncidentStatusUpdateView,
    IncidentAssignView,
    MyIncidentsView,
    UnassignedIncidentsView
)

urlpatterns = [
    path('', IncidentListCreateView.as_view(), name='incident_list_create'),
    path('<str:pk>/', IncidentDetailView.as_view(), name='incident_detail'),  # Changed to str for MongoDB ObjectId
    path('<str:pk>/status/', IncidentStatusUpdateView.as_view(), name='incident_status_update'),  # Changed to str for MongoDB ObjectId
    path('<str:pk>/assign/', IncidentAssignView.as_view(), name='incident_assign'),  # Changed to str for MongoDB ObjectId
    path('my-incidents/', MyIncidentsView.as_view(), name='my_incidents'),
    path('unassigned/', UnassignedIncidentsView.as_view(), name='unassigned_incidents'),
]

