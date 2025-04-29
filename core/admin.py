from django.contrib import admin
from .models import Category, Tag, Notification, Report, Post, Blog, Comment, Like, AdminLog

# Register your models here.
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Notification)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status', 'created_at')
    search_fields = ('reporter__username', 'details')
    date_hierarchy = 'created_at'

admin.site.register(Post)
admin.site.register(Blog)
admin.site.register(Comment)
admin.site.register(Like)

@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action_type', 'description', 'timestamp', 'target_user')
    list_filter = ('action_type', 'timestamp', 'admin')
    search_fields = ('description', 'admin__username', 'target_user__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'ip_address', 'content_type', 'object_id', 'content_object')
