from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'camera_id', 'severity', 'status', 'timestamp']
    list_filter = ['status', 'severity', 'alert_type', 'timestamp']
    search_fields = ['alert_type', 'camera_id__name']
    raw_id_fields = ['camera_id']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Alert Info', {'fields': ('camera_id', 'alert_type', 'severity')}),
        ('Status', {'fields': ('status', 'metadata')}),
        ('Timestamp', {'fields': ('timestamp',)}),
    )
    
    readonly_fields = ['timestamp']

