from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .utils import generate_avatar
import random
import string
from django.utils import timezone
from datetime import timedelta

class AdminRole(models.Model):
    """
    Admin role levels in the platform:
    - SUPER_ADMIN (Level 1): Highest authority with complete control
    - MODERATOR (Level 2): Day-to-day content moderation
    - SUPPORT (Level 3): User support and minor admin tasks
    """
    SUPER_ADMIN = 1
    MODERATOR = 2
    SUPPORT = 3
    
    ROLE_CHOICES = [
        (SUPER_ADMIN, _('Super Admin')),
        (MODERATOR, _('Moderator')),
        (SUPPORT, _('Support Staff')),
    ]
    
    name = models.CharField(max_length=100)
    level = models.IntegerField(choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    can_manage_users = models.BooleanField(default=False)
    can_manage_content = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_manage_admins = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_level_display()} ({self.name})"
    
    class Meta:
        ordering = ['level']
        verbose_name = _('Admin Role')
        verbose_name_plural = _('Admin Roles')

class CustomUser(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(max_length=200, blank=True)
    show_email = models.BooleanField(default=False)
    subscribers = models.ManyToManyField('self', symmetrical=False, related_name='subscribed_to', blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Admin role fields
    is_admin = models.BooleanField(default=False, help_text=_('Designates whether the user has any admin privileges'))
    admin_role = models.ForeignKey(
        AdminRole, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        help_text=_('The admin role assigned to this user')
    )
    admin_notes = models.TextField(blank=True, help_text=_('Notes about this admin user'))
    
    def save(self, *args, **kwargs):
        if not self.avatar and not self.pk:  # Only generate on first save
            self.avatar = generate_avatar(self)
        
        # Set is_admin based on admin_role
        if self.admin_role and not self.is_admin:
            self.is_admin = True
        elif not self.admin_role and self.is_admin:
            self.is_admin = False
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username
    
    @property
    def subscriber_count(self):
        return self.subscribers.count()
    
    @property
    def video_count(self):
        return self.videos.filter(is_published=True).count()
    
    @property
    def total_views(self):
        return self.videos.filter(is_published=True).aggregate(total=models.Sum('views'))['total'] or 0
    
    @property
    def is_super_admin(self):
        return self.is_admin and self.admin_role and self.admin_role.level == AdminRole.SUPER_ADMIN
    
    @property
    def is_moderator(self):
        return self.is_admin and self.admin_role and self.admin_role.level == AdminRole.MODERATOR
    
    @property
    def is_support_staff(self):
        return self.is_admin and self.admin_role and self.admin_role.level == AdminRole.SUPPORT
    
    def has_admin_permission(self, permission):
        """Check if the user has a specific admin permission"""
        if not self.is_admin or not self.admin_role:
            return False
            
        if self.is_super_admin:
            return True  # Super admins have all permissions
            
        # For other roles, check specific permissions
        return getattr(self.admin_role, permission, False)

class Subscription(models.Model):
    subscriber = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_subscriptions')
    channel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='channel_subscribers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subscriber', 'channel')
        
    def __str__(self):
        return f"{self.subscriber.username} -> {self.channel.username}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('reply', 'Reply'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications_received')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications_sent')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        return f"{self.sender} {self.notification_type}d your {self.content_type.model}"

    def get_absolute_url(self):
        if self.content_type.model == 'video':
            return reverse('videos:watch', kwargs={'slug': self.content_object.slug})
        elif self.content_type.model == 'post':
            return reverse('core:post_detail', kwargs={'pk': self.content_object.pk})
        elif self.content_type.model == 'comment':
            return self.content_object.get_absolute_url()
        return '/'

class PasswordResetOTP(models.Model):
    """Model to store OTPs for password reset"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_reset_otps')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"OTP for {self.user.username} ({self.otp})"
    
    def is_valid(self):
        """Check if the OTP is still valid"""
        return not self.is_used and timezone.now() <= self.expires_at
    
    @classmethod
    def generate_otp(cls, user):
        """Generate a 6-digit OTP for the user"""
        # Invalidate existing OTPs
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Generate new OTP
        otp = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timedelta(minutes=15)
        
        # Create and return new OTP
        return cls.objects.create(user=user, otp=otp, expires_at=expires_at)

class EmailVerificationOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='email_verification_otps')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Email verification OTP for {self.user.email}"
    
    class Meta:
        ordering = ['-created_at']
