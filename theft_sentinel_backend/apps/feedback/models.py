"""
Feedback Model
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Feedback(models.Model):
    """Feedback model for user feedback"""
    
    id = ObjectIdAutoField(primary_key=True)
    TYPE_CHOICES = [
        ('GENERAL', 'General'),
        ('INCIDENT', 'Incident Related'),
        ('FALSE_POSITIVE', 'False Positive'),
        ('TRUE_POSITIVE', 'True Positive'),
    ]
    
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='GENERAL', db_index=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'feedback'
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} feedback from {self.user_id.username}"

