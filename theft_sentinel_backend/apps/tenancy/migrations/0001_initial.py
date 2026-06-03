from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField
from bson import ObjectId


def _status_from_legacy(value):
    status = str(value or "PENDING").upper()
    if "APPROV" in status:
        return "APPROVED"
    if "SUSPEND" in status or "REJECT" in status:
        return "SUSPENDED"
    return "PENDING"


def _tenant_name(doc):
    return (
        doc.get("company_name")
        or doc.get("name")
        or doc.get("admin_name")
        or doc.get("email")
        or f"Tenant {doc['_id']}"
    )


def ensure_tenancy_collections(apps, schema_editor):
    """
    Create the new tenancy collections without failing if an older tenants
    collection already exists, and upgrade old tenant rows into tenant+branch.
    """
    db = schema_editor.connection.database
    existing = set(db.list_collection_names())

    if "tenants" not in existing:
        db.create_collection("tenants")
    if "branches" not in existing:
        db.create_collection("branches")

    tenants = db["tenants"]
    branches = db["branches"]
    now = timezone.now()

    tenants.create_index([("company_name", 1)], name="tenants_company_name_idx")
    tenants.create_index([("created_at", 1)], name="tenants_created_at_idx")
    branches.create_index([("tenant_id", 1)], name="branches_tenant_id_idx")
    branches.create_index([("branch_name", 1)], name="branches_branch_name_idx")
    branches.create_index([("admin_cnic", 1)], name="branches_admin_cnic_idx")
    branches.create_index([("admin_email", 1)], name="branches_admin_email_idx")
    branches.create_index([("status", 1)], name="branches_status_idx")
    branches.create_index([("created_at", 1)], name="branches_created_at_idx")
    branches.create_index(
        [("tenant_id", 1), ("branch_name", 1)],
        name="branches_tenant_branch_name_idx",
    )
    branches.create_index(
        [("status", 1), ("created_at", -1)],
        name="branches_status_created_at_idx",
    )

    for tenant in tenants.find({}):
        tenant_id = tenant["_id"]
        name = _tenant_name(tenant)
        set_fields = {}
        if not tenant.get("company_name"):
            set_fields["company_name"] = name
        if "company_address" not in tenant:
            set_fields["company_address"] = tenant.get("company_address", "")
        if "created_at" not in tenant:
            set_fields["created_at"] = now
        if set_fields:
            tenants.update_one({"_id": tenant_id}, {"$set": set_fields})

        if branches.find_one({"tenant_id": tenant_id}) is not None:
            continue

        branches.insert_one(
            {
                "_id": ObjectId(),
                "tenant_id": tenant_id,
                "branch_name": tenant.get("branch_name") or name,
                "admin_name": tenant.get("admin_name") or tenant.get("name") or "",
                "admin_cnic": tenant.get("admin_cnic") or tenant.get("cnic") or "",
                "admin_email": tenant.get("admin_email") or tenant.get("email") or "",
                "admin_phone": tenant.get("admin_phone") or tenant.get("phone") or "",
                "status": _status_from_legacy(tenant.get("status")),
                "created_at": tenant.get("created_at") or now,
            }
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        # No dependency on accounts here to avoid a circular dependency with accounts → tenancy (branch FK)
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_tenancy_collections, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="Tenant",
                    fields=[
                        ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                        ("company_name", models.CharField(db_index=True, max_length=255)),
                        ("company_address", models.CharField(blank=True, default="", max_length=512)),
                        ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
                    ],
                    options={"db_table": "tenants", "ordering": ["-created_at"]},
                ),
                migrations.CreateModel(
                    name="Branch",
                    fields=[
                        ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                        (
                            "tenant",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="branches",
                                to="tenancy.tenant",
                            ),
                        ),
                        ("branch_name", models.CharField(db_index=True, max_length=255)),
                        ("admin_name", models.CharField(max_length=255)),
                        ("admin_cnic", models.CharField(db_index=True, max_length=30)),
                        ("admin_email", models.EmailField(db_index=True, max_length=255)),
                        ("admin_phone", models.CharField(blank=True, default="", max_length=30)),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("PENDING", "Pending"),
                                    ("APPROVED", "Approved"),
                                    ("SUSPENDED", "Suspended"),
                                ],
                                db_index=True,
                                default="PENDING",
                                max_length=20,
                            ),
                        ),
                        ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
                    ],
                    options={"db_table": "branches", "ordering": ["-created_at"]},
                ),
                migrations.AddIndex(
                    model_name="branch",
                    index=models.Index(fields=["tenant", "branch_name"], name="branches_tenant_branch_name_idx"),
                ),
                migrations.AddIndex(
                    model_name="branch",
                    index=models.Index(fields=["status", "-created_at"], name="branches_status_created_at_idx"),
                ),
            ],
        ),
    ]

