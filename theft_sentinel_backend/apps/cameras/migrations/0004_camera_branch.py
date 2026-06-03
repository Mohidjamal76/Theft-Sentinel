from django.db import migrations, models
import django.db.models.deletion


def backfill_camera_branches(apps, schema_editor):
    db = schema_editor.connection.database
    collections = set(db.list_collection_names())
    if "cameras" not in collections or "branches" not in collections:
        return

    cameras = db["cameras"]
    for branch in db["branches"].find({}, {"_id": 1, "tenant_id": 1}):
        tenant_id = branch.get("tenant_id")
        if tenant_id is None:
            continue
        cameras.update_many(
            {
                "tenant_id": tenant_id,
                "$or": [{"branch_id": {"$exists": False}}, {"branch_id": None}],
            },
            {"$set": {"branch_id": branch["_id"]}},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("cameras", "0003_camera_ai_monitoring_enabled"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="camera",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cameras",
                to="tenancy.branch",
            ),
        ),
        migrations.RunPython(backfill_camera_branches, migrations.RunPython.noop),
    ]

