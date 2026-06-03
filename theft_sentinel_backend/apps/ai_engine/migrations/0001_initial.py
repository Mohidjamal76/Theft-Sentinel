# Generated migration for AI Engine models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_mongodb_backend.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cameras', '0001_initial'),
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIInference',
            fields=[
                ('id', django_mongodb_backend.fields.ObjectIdAutoField(primary_key=True, serialize=False)),
                ('detections', models.JSONField(default=list)),
                ('poses', models.JSONField(default=list)),
                ('tracks', models.JSONField(default=list)),
                ('classification', models.CharField(default='normal', max_length=50)),
                ('confidence', models.FloatField(default=0.0)),
                ('frame_metadata', models.JSONField(default=dict)),
                ('processing_time_ms', models.FloatField(default=0.0)),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('alert', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_inferences', to='alerts.alert')),
                ('camera_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ai_inferences', to='cameras.camera')),
            ],
            options={
                'verbose_name': 'AI Inference',
                'verbose_name_plural': 'AI Inferences',
                'db_table': 'ai_inferences',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='DetectionTrack',
            fields=[
                ('id', django_mongodb_backend.fields.ObjectIdAutoField(primary_key=True, serialize=False)),
                ('track_id', models.IntegerField()),
                ('object_type', models.CharField(max_length=50)),
                ('first_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('frame_count', models.IntegerField(default=0)),
                ('hand_in_bag_frames', models.IntegerField(default=0)),
                ('hand_in_torso_frames', models.IntegerField(default=0)),
                ('fast_wrist_frames', models.IntegerField(default=0)),
                ('near_object_frames', models.IntegerField(default=0)),
                ('concealment_events', models.IntegerField(default=0)),
                ('ml_theft_score', models.FloatField(default=0.0)),
                ('max_theft_score', models.FloatField(default=0.0)),
                ('is_suspicious', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('camera_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detection_tracks', to='cameras.camera')),
            ],
            options={
                'verbose_name': 'Detection Track',
                'verbose_name_plural': 'Detection Tracks',
                'db_table': 'detection_tracks',
                'ordering': ['-last_seen'],
            },
        ),
        migrations.AddIndex(
            model_name='detectiontrack',
            index=models.Index(fields=['camera_id', 'track_id'], name='detection_t_camera__idx'),
        ),
        migrations.AddIndex(
            model_name='detectiontrack',
            index=models.Index(fields=['is_active', 'is_suspicious'], name='detection_t_is_acti_idx'),
        ),
    ]

