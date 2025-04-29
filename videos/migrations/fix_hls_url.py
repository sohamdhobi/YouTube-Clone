from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('videos', '0006_add_moderation_fields'),  # Updated to point to the latest migration
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='hls_url',
            field=models.URLField(blank=True, help_text='URL to the HLS manifest file (.m3u8)', max_length=500, null=True),
        ),
    ] 