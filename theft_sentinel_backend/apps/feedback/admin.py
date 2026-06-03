from django.contrib import admin
from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'type', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['message', 'user_id__username']
    raw_id_fields = ['user_id']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Feedback Info', {'fields': ('user_id', 'type')}),
        ('Content', {'fields': ('message',)}),
        ('Timestamp', {'fields': ('created_at',)}),
    )
    
    readonly_fields = ['created_at']

