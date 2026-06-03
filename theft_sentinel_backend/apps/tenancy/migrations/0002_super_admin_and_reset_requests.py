from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0001_initial"),
        ("accounts", "0004_user_branch_and_super_admin"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuperAdminProfile",
            fields=[
                ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="super_admin_profile",
                        to="accounts.user",
                    ),
                ),
                ("full_name", models.CharField(max_length=255)),
                ("phone_number", models.CharField(blank=True, default="", max_length=30)),
                ("partners_count", models.PositiveSmallIntegerField(default=0)),
                ("partners", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
            ],
            options={"db_table": "super_admin_profile", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BranchPasswordResetRequest",
            fields=[
                ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branch_password_reset_requests",
                        to="accounts.user",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="password_reset_requests",
                        to="tenancy.branch",
                    ),
                ),
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_password_reset_requests",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"db_table": "branch_password_reset_requests", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="branchpasswordresetrequest",
            index=models.Index(fields=["status", "-created_at"], name="bprr_status_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="branchpasswordresetrequest",
            index=models.Index(fields=["branch", "-created_at"], name="bprr_branch_created_at_idx"),
        ),
    ]

