from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0002_remove_image_creator_remove_comment_image_and_more'),
    ]

    operations = [
        # First remove the old Report model
        migrations.DeleteModel(
            name='Report',
        ),
        
        # Then create a new Report model with the correct structure
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('reason', models.CharField(choices=[
                    ('inappropriate', 'Inappropriate Content'),
                    ('copyright', 'Copyright Violation'),
                    ('harmful', 'Harmful or Dangerous'),
                    ('misinformation', 'Misinformation'),
                    ('hate_speech', 'Hate Speech'),
                    ('harassment', 'Harassment or Bullying'),
                    ('spam', 'Spam or Misleading'),
                    ('violence', 'Violent or Graphic Content'),
                    ('other', 'Other')
                ], max_length=20)),
                ('details', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending Review'),
                    ('reviewed', 'Reviewed'),
                    ('resolved', 'Resolved'),
                    ('rejected', 'Rejected')
                ], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports_filed', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports_reviewed', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ] 