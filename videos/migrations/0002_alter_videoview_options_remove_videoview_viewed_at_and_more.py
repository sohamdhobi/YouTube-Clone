# Generated by Django 5.1.7 on 2025-04-09 04:49

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0001_add_is_processing'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='videoview',
            options={'verbose_name': 'Video View', 'verbose_name_plural': 'Video Views'},
        ),
        migrations.RemoveField(
            model_name='videoview',
            name='viewed_at',
        ),
        migrations.AddField(
            model_name='videoview',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='videoview',
            name='device',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='videoview',
            name='is_recommendation',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='videoview',
            name='referrer',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='videoview',
            name='session_id',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AddField(
            model_name='videoview',
            name='view_time',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='videoview',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='videoview',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='video_views', to=settings.AUTH_USER_MODEL),
        ),
    ]
