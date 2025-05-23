# Generated by Django 5.1.7 on 2025-03-26 12:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='video',
            name='category',
        ),
        migrations.AlterModelOptions(
            name='playlistitem',
            options={'ordering': ['order']},
        ),
        migrations.RenameField(
            model_name='playlistitem',
            old_name='position',
            new_name='order',
        ),
        migrations.RenameField(
            model_name='videoview',
            old_name='created_at',
            new_name='viewed_at',
        ),
        migrations.AlterUniqueTogether(
            name='playlistitem',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='videoview',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='playlist',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='video',
            name='tags',
        ),
        migrations.AddField(
            model_name='playlist',
            name='videos',
            field=models.ManyToManyField(related_name='playlists', through='videos.PlaylistItem', to='videos.video'),
        ),
        migrations.AddField(
            model_name='video',
            name='blog_content',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='video',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='images/'),
        ),
        migrations.AlterField(
            model_name='playlist',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='playlists', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='playlist',
            name='title',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='playlistitem',
            name='playlist',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='videos.playlist'),
        ),
        migrations.AlterField(
            model_name='video',
            name='content_type',
            field=models.CharField(choices=[('video', 'Video'), ('photo', 'Photo'), ('blog', 'Blog Post')], default='video', max_length=10),
        ),
        migrations.AlterField(
            model_name='video',
            name='creator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='videos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='video',
            name='description',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='video',
            name='slug',
            field=models.SlugField(blank=True, max_length=200, unique=True),
        ),
        migrations.AlterField(
            model_name='video',
            name='title',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='videoview',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='playlistitem',
            unique_together={('playlist', 'video')},
        ),
        migrations.DeleteModel(
            name='Category',
        ),
    ]
