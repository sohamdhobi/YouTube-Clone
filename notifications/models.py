from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    """
    A notification model to handle system notifications for users.
    Uses a generic foreign key to reference any type of object.
    """
    NOTIFICATION_TYPES = (
        ('moderation', 'Content Moderation'),
        ('comment', 'New Comment'),
        ('like', 'New Like'),
        ('subscription', 'New Subscription'),
        ('warning', 'Account Warning'),
        ('system', 'System Notification'),
        ('report', 'Content Report'),
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='system_notifications',
        on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='system_actions',
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    unread = models.BooleanField(default=True)
    
    # Content type for the related object
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE,
        related_name='system_notifications',
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Type of notification
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    
    # Optional URL to redirect to when clicked
    url = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['recipient', 'unread']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.recipient.username} - {self.verb}"
    
    def mark_as_read(self):
        if self.unread:
            self.unread = False
            self.save()
    
    @classmethod
    def create_moderation_notification(cls, recipient, content_object, status, message=None, actor=None):
        """Create a moderation notification"""
        content_type = ContentType.objects.get_for_model(content_object)
        
        verb = f"Your content has been {status}"
        description = message or f"Your video titled '{content_object.title}' has been {status} by our moderation team."
        
        # Create video detail URL
        url = f"/videos/{content_object.id}/"
        
        return cls.objects.create(
            recipient=recipient,
            actor=actor,
            verb=verb,
            description=description,
            content_type=content_type,
            object_id=content_object.id,
            notification_type='moderation',
            url=url
        ) 