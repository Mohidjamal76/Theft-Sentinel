"""
URL configuration for personnel app
"""
from django.urls import path
from .views import (
    PersonnelListCreateView,
    PersonnelDetailView,
    MyPersonnelProfileView
)

urlpatterns = [
    path('', PersonnelListCreateView.as_view(), name='personnel_list_create'),
    path('<int:pk>/', PersonnelDetailView.as_view(), name='personnel_detail'),
    path('me/', MyPersonnelProfileView.as_view(), name='my_personnel_profile'),
]

