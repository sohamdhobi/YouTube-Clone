from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'verb', 'timestamp', 'unread')
    list_filter = ('notification_type', 'unread', 'timestamp')
    search_fields = ('recipient__username', 'verb', 'description')
    date_hierarchy = 'timestamp'
    readonly_fields = ('content_type', 'object_id', 'content_object')
