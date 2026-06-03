"""
URL configuration for mobile app
"""
from django.urls import path
from .views import (
    NotificationListView,
    MyNotificationsView,
    SendSMSView,
    SendEmailView,
    BulkNotificationView
)

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/me/', MyNotificationsView.as_view(), name='my_notifications'),
    path('send-sms/', SendSMSView.as_view(), name='send_sms'),
    path('send-email/', SendEmailView.as_view(), name='send_email'),
    path('send-bulk/', BulkNotificationView.as_view(), name='send_bulk'),
]

