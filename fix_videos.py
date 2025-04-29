import django
import os
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "youtube_clone.settings")
django.setup()

from videos.models import Video

def publish_videos():
    count = 0
    for video in Video.objects.all():
        # Set moderation to approved
        video.requires_moderation = False  # Disable moderation requirement
        video.moderation_status = 'approved'
        video.moderated_at = timezone.now()
        video.is_published = True
        video.save()
        count += 1
        print(f"Published: {video.title}")
    
    print(f"Total videos published: {count}")

if __name__ == "__main__":
    publish_videos() 