from django.contrib import admin
from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'alert_id', 'assigned_to', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['notes', 'assigned_to__username']
    raw_id_fields = ['alert_id', 'assigned_to']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Incident Info', {'fields': ('alert_id', 'assigned_to', 'status')}),
        ('Details', {'fields': ('notes',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at']

