from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Subscription, Notification, AdminRole

class AdminRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'description', 'can_manage_users', 'can_manage_content', 'can_manage_settings', 'can_manage_admins')
    list_filter = ('level', 'can_manage_users', 'can_manage_content', 'can_manage_settings', 'can_manage_admins')
    search_fields = ('name', 'description')
    ordering = ('level',)
    fieldsets = (
        (None, {'fields': ('name', 'level', 'description')}),
        (_('Permissions'), {'fields': ('can_manage_users', 'can_manage_content', 'can_manage_settings', 'can_manage_admins')}),
    )

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_admin')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_admin', 'admin_role')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # Add 'date_joined' to readonly_fields
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'avatar', 'bio')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Admin Role', {'fields': ('is_admin', 'admin_role', 'admin_notes')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    def get_admin_role(self, obj):
        return obj.admin_role.name if obj.admin_role else '-'
    get_admin_role.short_description = _('Admin Role')
    get_admin_role.admin_order_field = 'admin_role__name'

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'channel', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('subscriber__username', 'channel__username')
    date_hierarchy = 'created_at'

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'sender', 'notification_type', 'read', 'created_at')
    list_filter = ('notification_type', 'read', 'created_at')
    search_fields = ('recipient__username', 'sender__username')
    date_hierarchy = 'created_at'

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(AdminRole, AdminRoleAdmin)
