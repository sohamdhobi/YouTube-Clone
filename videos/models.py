from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
import os
import uuid
from django.utils import timezone

class Video(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('video', 'Video'),
        ('photo', 'Photo'),
        ('blog', 'Blog Post'),
    )
    
    MODERATION_STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    file = models.FileField(upload_to='videos/', null=True, blank=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES, default='video')
    blog_content = models.TextField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    hls_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL to the HLS manifest file (.m3u8)")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='videos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    is_published = models.BooleanField(default=True)
    
    # Processing field
    is_processing = models.BooleanField(default=False, help_text="Whether this video is currently being processed")
    
    # Moderation fields
    requires_moderation = models.BooleanField(default=True, help_text="Whether this content requires moderation before publishing")
    moderation_status = models.CharField(max_length=10, choices=MODERATION_STATUS_CHOICES, default='pending')
    moderation_notes = models.TextField(blank=True, null=True)
    moderated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='moderated_content')
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Create a slug from the title
            base_slug = slugify(self.title)
            
            # If slug is empty (e.g., title only had special characters), use content type + id
            if not base_slug:
                base_slug = f"{self.content_type}-content"
            
            # Add random suffix to ensure uniqueness
            unique_id = str(uuid.uuid4())[:8]
            self.slug = f"{base_slug}-{unique_id}"
            
        # Set published status based on moderation settings
        if self.requires_moderation and self.moderation_status != 'approved':
            self.is_published = False
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def comment_count(self):
        return self.comments.count()

class Playlist(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='playlists')
    videos = models.ManyToManyField(Video, through='PlaylistItem', related_name='playlists')
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('playlist', 'video')
    
    def __str__(self):
        return f'{self.video.title} in {self.playlist.title}'

class VideoView(models.Model):
    """
    Tracks individual video views including watch time.
    Used for video popularity metrics and recommendation engine training.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='video_views', null=True, blank=True)
    video = models.ForeignKey('Video', on_delete=models.CASCADE, related_name='video_views')
    created_at = models.DateTimeField(default=timezone.now)  # Use default instead of auto_now_add
    view_time = models.PositiveIntegerField(default=0)  # time in seconds
    session_id = models.CharField(max_length=40, blank=True, null=True)  # For anonymous users
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Additional details about the view
    referrer = models.CharField(max_length=255, blank=True, null=True)  # Where the view came from
    device = models.CharField(max_length=50, blank=True, null=True)  # Device type
    is_recommendation = models.BooleanField(default=False)  # Whether this view came from a recommendation
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} viewed {self.video.title} for {self.view_time} seconds"
    
    class Meta:
        verbose_name = 'Video View'
        verbose_name_plural = 'Video Views'
        
    @classmethod
    def record_view(cls, video, user=None, session_id=None, ip_address=None, 
                   view_time=0, referrer=None, device=None, is_recommendation=False):
        """
        Record a view with all associated metadata
        
        Args:
            video: Video object
            user: User object or None for anonymous
            session_id: Session ID string for anonymous users
            ip_address: IP address string
            view_time: View time in seconds
            referrer: Referrer URL string
            device: Device type string
            is_recommendation: Boolean indicating if view came from recommendation
            
        Returns:
            The created VideoView object
        """
        # Create the view record
        view = cls(
            video=video,
            user=user,
            session_id=session_id,
            ip_address=ip_address,
            view_time=view_time,
            referrer=referrer,
            device=device,
            is_recommendation=is_recommendation
        )
        view.save()
        
        # Update the video's view count
        video.views = models.F('views') + 1
        video.save(update_fields=['views'])
        
        return view
