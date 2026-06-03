from django.contrib import admin
from .models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'zone', 'status', 'created_at']
    list_filter = ['status', 'zone', 'created_at']
    search_fields = ['name', 'location', 'zone']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'location', 'zone')}),
        ('Technical', {'fields': ('rtsp_url', 'status')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )
    
    readonly_fields = ['created_at']

