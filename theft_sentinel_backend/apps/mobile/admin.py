from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'notification_type', 'recipient', 'status', 'created_at', 'sent_at']
    list_filter = ['notification_type', 'status', 'created_at']
    search_fields = ['recipient', 'message', 'user__username']
    raw_id_fields = ['user']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Info', {'fields': ('user', 'notification_type', 'recipient')}),
        ('Content', {'fields': ('subject', 'message')}),
        ('Status', {'fields': ('status', 'error_message')}),
        ('Timestamps', {'fields': ('created_at', 'sent_at')}),
    )
    
    readonly_fields = ['created_at', 'sent_at']

