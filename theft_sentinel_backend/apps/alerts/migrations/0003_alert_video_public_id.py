# Generated manually — Cloudinary asset id for reliable delete

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0002_alert_video_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='video_public_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
