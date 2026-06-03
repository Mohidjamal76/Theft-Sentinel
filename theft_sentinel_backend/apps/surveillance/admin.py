from django.contrib import admin
from .models import SurveillanceEvent


@admin.register(SurveillanceEvent)
class SurveillanceEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'camera_id', 'event_type', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['event_type', 'camera_id__name']
    raw_id_fields = ['camera_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Event Info', {'fields': ('camera_id', 'event_type', 'frame_url')}),
        ('AI Data', {'fields': ('ai_data',)}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    readonly_fields = ['created_at']

