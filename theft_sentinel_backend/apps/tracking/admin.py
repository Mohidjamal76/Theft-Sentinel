from django.contrib import admin
from .models import TrackingRecord


@admin.register(TrackingRecord)
class TrackingRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'person_id', 'camera_id', 'timestamp']
    list_filter = ['timestamp', 'camera_id']
    search_fields = ['person_id', 'camera_id__name']
    raw_id_fields = ['camera_id']
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Tracking Info', {'fields': ('person_id', 'camera_id')}),
        ('Vector Data', {'fields': ('vector',)}),
        ('Timestamp', {'fields': ('timestamp',)}),
    )
    
    readonly_fields = ['timestamp']

