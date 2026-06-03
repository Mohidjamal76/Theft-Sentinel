import re

from django.db import migrations, models
from django.utils import timezone
from django_mongodb_backend.fields import ObjectIdAutoField


def _normalize_cnic(value):
    digits = re.sub(r"[\s-]+", "", str(value or "").strip())
    if len(digits) != 13 or not digits.isdigit():
        return None, None
    formatted = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return digits, formatted


def backfill_cnic_registry(apps, schema_editor):
    db = schema_editor.connection.database
    existing = set(db.list_collection_names())
    if "cnic_registry" not in existing:
        db.create_collection("cnic_registry")

    registry = db["cnic_registry"]
    index_info = registry.index_information()
    if not any(info.get("key") == [("cnic", 1)] for info in index_info.values()):
        registry.create_index([("cnic", 1)], unique=True, name="cnic_registry_cnic_uniq")
    if not any(info.get("key") == [("owner_type", 1), ("owner_id", 1)] for info in index_info.values()):
        registry.create_index([("owner_type", 1), ("owner_id", 1)], name="cnic_reg_owner_idx")

    now = timezone.now()
    seen = set()

    if "branches" in existing:
        branches = db["branches"]
        for branch in branches.find({}, {"_id": 1, "admin_cnic": 1}):
            key, formatted = _normalize_cnic(branch.get("admin_cnic"))
            if not key:
                continue
            branches.update_one({"_id": branch["_id"]}, {"$set": {"admin_cnic": formatted}})
            owner_id = str(branch["_id"])
            if key in seen or registry.find_one({"cnic": key}):
                continue
            registry.insert_one(
                {
                    "cnic": key,
                    "owner_type": "BRANCH_ADMIN",
                    "owner_id": owner_id,
                    "created_at": now,
                }
            )
            seen.add(key)

    if "super_admin_profile" in existing:
        profiles = db["super_admin_profile"]
        for profile in profiles.find({}, {"_id": 1, "partners": 1}):
            partners = list(profile.get("partners") or [])
            changed = False
            for idx, partner in enumerate(partners):
                if not isinstance(partner, dict):
                    continue
                key, formatted = _normalize_cnic(partner.get("cnic"))
                if not key:
                    continue
                if partner.get("cnic") != formatted:
                    partner["cnic"] = formatted
                    changed = True
                owner_id = f"{profile['_id']}:{idx}"
                if key in seen or registry.find_one({"cnic": key}):
                    continue
                registry.insert_one(
                    {
                        "cnic": key,
                        "owner_type": "SUPER_ADMIN_PARTNER",
                        "owner_id": owner_id,
                        "created_at": now,
                    }
                )
                seen.add(key)
            if changed:
                profiles.update_one({"_id": profile["_id"]}, {"$set": {"partners": partners}})


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0003_rename_branches_tenant_branch_name_idx_branches_tenant__c5ffaa_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CnicRegistry",
            fields=[
                ("id", ObjectIdAutoField(primary_key=True, serialize=False)),
                ("cnic", models.CharField(db_index=True, max_length=13, unique=True)),
                ("owner_type", models.CharField(db_index=True, max_length=100)),
                ("owner_id", models.CharField(db_index=True, max_length=100)),
                ("created_at", models.DateTimeField(db_index=True, default=timezone.now)),
            ],
            options={"db_table": "cnic_registry", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="cnicregistry",
            index=models.Index(fields=["owner_type", "owner_id"], name="cnic_reg_owner_idx"),
        ),
        migrations.RunPython(backfill_cnic_registry, migrations.RunPython.noop),
    ]
