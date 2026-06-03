# Generated manually for alert clip storage

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='video_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
