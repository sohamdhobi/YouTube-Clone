from django.db import migrations, models
import django.utils.timezone
from django.db import models
from django.conf import settings
from django.db.models import deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('videos', '0005_video_hls_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='requires_moderation',
            field=models.BooleanField(default=True, help_text='Whether this content requires moderation before publishing'),
        ),
        migrations.AddField(
            model_name='video',
            name='moderation_status',
            field=models.CharField(choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10),
        ),
        migrations.AddField(
            model_name='video',
            name='moderation_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='video',
            name='moderated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=deletion.SET_NULL, related_name='moderated_content', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='video',
            name='moderated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ] 