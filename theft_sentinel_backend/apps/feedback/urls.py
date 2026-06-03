"""
URL configuration for feedback app
"""
from django.urls import path
from .views import (
    FeedbackListCreateView,
    FeedbackDetailView,
    MyFeedbackView,
    FeedbackStatsView,
    FeedbackDeleteView
)

urlpatterns = [
    path('', FeedbackListCreateView.as_view(), name='feedback_list_create'),
    path('me/', MyFeedbackView.as_view(), name='my_feedback'),  # Must come before <str:pk> to avoid matching "me" as pk
    path('stats/', FeedbackStatsView.as_view(), name='feedback_stats'),
    path('<str:pk>/', FeedbackDetailView.as_view(), name='feedback_detail'),
    path('<str:pk>/delete/', FeedbackDeleteView.as_view(), name='feedback_delete'),
]

