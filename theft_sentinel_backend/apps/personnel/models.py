"""
Personnel Model - Staff profiles with zone assignments
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Personnel(models.Model):
    """Personnel model for staff profiles"""
    
    id = ObjectIdAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='personnel_profile'
    )
    phone = models.CharField(max_length=20)
    assigned_zones = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'personnel'
        verbose_name = 'Personnel'
        verbose_name_plural = 'Personnel'
    
    def __str__(self):
        return f"{self.user.username} - {self.phone}"

