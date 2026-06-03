from django.conf import settings
from django.db import models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class SupportQuery(models.Model):
    STATUS_PENDING_BRANCH_ADMIN = "PENDING_BRANCH_ADMIN"
    STATUS_PENDING_SUPER_ADMIN = "PENDING_SUPER_ADMIN"
    STATUS_ANSWERED = "ANSWERED"

    STATUS_CHOICES = [
        (STATUS_PENDING_BRANCH_ADMIN, "Pending (Branch Admin)"),
        (STATUS_PENDING_SUPER_ADMIN, "Pending (Super Admin)"),
        (STATUS_ANSWERED, "Answered"),
    ]

    id = ObjectIdAutoField(primary_key=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_queries_sent"
    )
    branch = models.ForeignKey(
        "tenancy.Branch", on_delete=models.CASCADE, related_name="support_queries"
    )
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, db_index=True)

    message = models.TextField()
    answer = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_queries_answered",
    )

    class Meta:
        db_table = "support_queries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status", "-created_at"], name="support_que_branch__7b34b9_idx"),
            models.Index(fields=["sender", "-created_at"], name="support_que_sender__eeb9a1_idx"),
        ]

    def __str__(self):
        return f"Query({self.sender.email}, {self.status})"

