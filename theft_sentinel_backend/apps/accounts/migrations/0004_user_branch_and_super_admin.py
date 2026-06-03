from django.db import migrations, models
import django.db.models.deletion


def backfill_user_branches(apps, schema_editor):
    db = schema_editor.connection.database
    collections = set(db.list_collection_names())
    if "accounts_user" not in collections or "branches" not in collections:
        return

    users = db["accounts_user"]
    for branch in db["branches"].find({}, {"_id": 1, "tenant_id": 1}):
        tenant_id = branch.get("tenant_id")
        if tenant_id is None:
            continue
        users.update_many(
            {
                "tenant_id": tenant_id,
                "$or": [{"branch_id": {"$exists": False}}, {"branch_id": None}],
            },
            {"$set": {"branch_id": branch["_id"]}},
        )


def make_username_non_unique(apps, schema_editor):
    db = schema_editor.connection.database
    if "accounts_user" not in set(db.list_collection_names()):
        return

    users = db["accounts_user"]
    has_non_unique_username_index = False
    for name, info in list(users.index_information().items()):
        if info.get("key") != [("username", 1)]:
            continue
        if info.get("unique"):
            users.drop_index(name)
        else:
            has_non_unique_username_index = True
    if not has_non_unique_username_index:
        users.create_index([("username", 1)], name="accounts_user_username_idx")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_passwordresetaudit"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="tenancy.branch",
            ),
        ),
        migrations.RunPython(backfill_user_branches, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(make_username_non_unique, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="username",
                    field=models.CharField(db_index=True, max_length=150),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("SUPER_ADMIN", "Super Administrator"),
                    ("ADMIN", "Administrator"),
                    ("SECURITY_INCHARGE", "Security In-Charge"),
                    ("SECURITY_GUARD", "Security Guard"),
                ],
                default="SECURITY_GUARD",
                max_length=20,
            ),
        ),
    ]

