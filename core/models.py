from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import numpy as np
from django.utils.text import slugify
from django.utils import timezone
from videos.models import Video

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    videos = models.ManyToManyField(Video, related_name='categories', blank=True)
    
    class Meta:
        verbose_name_plural = 'categories'
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)
    videos = models.ManyToManyField(Video, related_name='tags', blank=True)
    
    def __str__(self):
        return self.name

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('comment', 'New Comment'),
        ('like', 'New Like'),
        ('subscribe', 'New Subscriber'),
        ('video', 'New Video'),
    )
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actions')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, null=True, blank=True)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.actor.username} {self.notification_type} -> {self.recipient.username}'

class Report(models.Model):
    REASON_CHOICES = (
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('harmful', 'Harmful or Dangerous'),
        ('misinformation', 'Misinformation'),
        ('hate_speech', 'Hate Speech'),
        ('harassment', 'Harassment or Bullying'),
        ('spam', 'Spam or Misleading'),
        ('violence', 'Violent or Graphic Content'),
        ('adult', 'Adult/Sexual Content'),
        ('child_safety', 'Child Safety Concern'),
        ('terrorism', 'Terrorism/Extremism'),
        ('illegal_activity', 'Illegal Activity'),
        ('impersonation', 'Impersonation'),
        ('privacy', 'Privacy Violation'),
        ('false_information', 'False Information'),
        ('self_harm', 'Self-Harm Content'),
        ('trademark', 'Trademark Violation'),
        ('other', 'Other')
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected')
    )
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_filed')
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_reviewed')
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_resolved')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Report: {self.get_reason_display()} by {self.reporter.username}"

class Post(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, max_length=255)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('core:post_detail', kwargs={'slug': self.slug})

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

class Blog(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogs')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, max_length=255)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_blogs', blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('core:blog_detail', kwargs={'slug': self.slug})

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='all_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_comments', blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # Generic foreign key for different types of content
    video = models.ForeignKey(Video, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')
    blog = models.ForeignKey(Blog, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')

    @property
    def like_count(self):
        return self.likes.count()

    class Meta:
        ordering = ['-created_at']

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='all_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic foreign key for different types of content
    video = models.ForeignKey(Video, null=True, blank=True, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name='post_likes')
    blog = models.ForeignKey(Blog, null=True, blank=True, on_delete=models.CASCADE, related_name='blog_likes')
    comment = models.ForeignKey(Comment, null=True, blank=True, on_delete=models.CASCADE, related_name='comment_likes')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'video'],
                condition=models.Q(video__isnull=False),
                name='unique_video_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'post'],
                condition=models.Q(post__isnull=False),
                name='unique_post_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'blog'],
                condition=models.Q(blog__isnull=False),
                name='unique_blog_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                condition=models.Q(comment__isnull=False),
                name='unique_comment_like'
            ),
        ]

class AdminLog(models.Model):
    """
    Model to track admin actions including moderation, warnings, and other administrative tasks.
    """
    ACTION_TYPES = (
        ('moderation', 'Content Moderation'),
        ('warning', 'User Warning'),
        ('delete', 'Content Deletion'),
        ('user_action', 'User Account Action'),
        ('system', 'System Action'),
        ('other', 'Other Action')
    )
    
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Generic relation to connect to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # For user-specific actions
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='received_admin_actions'
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Log'
        verbose_name_plural = 'Admin Logs'
    
    def __str__(self):
        return f"{self.admin.username} - {self.get_action_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class VideoEmbedding(models.Model):
    """
    Stores BERT embeddings for videos to be used by the recommendation engine.
    """
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='embedding')
    embedding_vector = models.BinaryField()  # Stores the serialized numpy array
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Embedding for {self.video.title}"
    
    def get_vector(self):
        """
        Deserialize the stored binary data into a numpy array
        """
        return np.frombuffer(self.embedding_vector, dtype=np.float32)
    
    def set_vector(self, vector):
        """
        Serialize a numpy array for storage
        """
        self.embedding_vector = vector.astype(np.float32).tobytes()
    
    @classmethod
    def create_from_video(cls, video, vector):
        """
        Create a new embedding or update if it already exists
        """
        obj, created = cls.objects.update_or_create(
            video=video,
            defaults={'embedding_vector': vector.astype(np.float32).tobytes()}
        )
        return obj

class UserEmbedding(models.Model):
    """
    Stores user preference embeddings based on their interactions.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='embedding')
    embedding_vector = models.BinaryField()  # Stores the serialized numpy array
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preference embedding for {self.user.username}"
    
    def get_vector(self):
        """
        Deserialize the stored binary data into a numpy array
        """
        return np.frombuffer(self.embedding_vector, dtype=np.float32)
    
    def set_vector(self, vector):
        """
        Serialize a numpy array for storage
        """
        self.embedding_vector = vector.astype(np.float32).tobytes()
    
    @classmethod
    def create_from_user(cls, user, vector):
        """
        Create a new embedding or update if it already exists
        """
        obj, created = cls.objects.update_or_create(
            user=user,
            defaults={'embedding_vector': vector.astype(np.float32).tobytes()}
        )
        return obj

class BanditStats(models.Model):
    """
    Stores statistics for the Contextual Bandit algorithm.
    """
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='bandit_stats')
    impression_count = models.PositiveIntegerField(default=0)  # Number of times video was shown
    click_count = models.PositiveIntegerField(default=0)  # Number of times video was clicked
    total_watch_time = models.PositiveIntegerField(default=0)  # Total watch time in seconds
    reward_sum = models.FloatField(default=0.0)  # Sum of rewards
    
    # UCB exploration parameter
    ucb_score = models.FloatField(default=0.0)
    
    # Timestamps for tracking
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bandit stats for {self.video.title}"
    
    def update_stats(self, clicked=False, watch_time=0):
        """
        Update statistics after a recommendation is made
        """
        self.impression_count += 1
        
        if clicked:
            self.click_count += 1
            self.total_watch_time += watch_time
            
            # Calculate reward based on watch time
            reward = min(1.0, watch_time / (self.video.duration or 300))  # Normalize, default to 5 min if no duration
            self.reward_sum += reward
            
        # Update UCB score
        self.update_ucb_score()
        self.save()
    
    def update_ucb_score(self):
        """
        Update the Upper Confidence Bound score
        UCB = average_reward + exploration_bonus
        """
        import math
        
        # Avoid division by zero
        if self.impression_count == 0:
            self.ucb_score = float('inf')
            return
            
        # Average reward
        average_reward = self.reward_sum / self.impression_count if self.impression_count > 0 else 0
        
        # Exploration bonus (sqrt(2 * ln(total_count) / arm_count))
        exploration_bonus = math.sqrt(2 * math.log(BanditStats.objects.count() or 1) / self.impression_count)
        
        # UCB score
        self.ucb_score = average_reward + exploration_bonus

class ContentEmbedding(models.Model):
    """Model to store pre-computed BERT embeddings for content"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    embedding = models.BinaryField(null=True, blank=True, help_text="BERT embedding vector for the content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"Embedding for {self.content_object}"
