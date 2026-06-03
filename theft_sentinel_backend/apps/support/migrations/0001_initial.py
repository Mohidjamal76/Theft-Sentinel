from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenancy", "0001_initial"),
        ("accounts", "0004_user_branch_and_super_admin"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportQuery",
            fields=[
                ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_queries_sent",
                        to="accounts.user",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_queries",
                        to="tenancy.branch",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING_BRANCH_ADMIN", "Pending (Branch Admin)"),
                            ("PENDING_SUPER_ADMIN", "Pending (Super Admin)"),
                            ("ANSWERED", "Answered"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ("message", models.TextField()),
                ("answer", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
                ("answered_at", models.DateTimeField(blank=True, null=True)),
                (
                    "answered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="support_queries_answered",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"db_table": "support_queries", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="supportquery",
            index=models.Index(fields=["branch", "status", "-created_at"], name="sq_branch_status_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="supportquery",
            index=models.Index(fields=["sender", "-created_at"], name="sq_sender_created_at_idx"),
        ),
    ]

