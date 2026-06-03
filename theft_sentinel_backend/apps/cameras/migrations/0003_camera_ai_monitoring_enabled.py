from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cameras', '0002_camera_last_feed_timestamp_alter_camera_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='camera',
            name='ai_monitoring_enabled',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Whether AI continuous monitoring is enabled for this camera',
            ),
        ),
    ]
