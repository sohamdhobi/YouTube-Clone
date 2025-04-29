from django import template

register = template.Library()

@register.filter
def filter_super_admins(admins):
    """Filter super admins (level 1) from a queryset of admin users."""
    return admins.filter(admin_role__level=1)

@register.filter
def filter_moderators(admins):
    """Filter moderators (level 2) from a queryset of admin users."""
    return admins.filter(admin_role__level=2)

@register.filter
def filter_support_staff(admins):
    """Filter support staff (level 3) from a queryset of admin users."""
    return admins.filter(admin_role__level=3)

@register.filter
def has_permission(user, permission):
    """
    Usage: {% if request.user|has_permission:"can_manage_content" %}
    """
    if user.is_admin and hasattr(user, 'admin_role') and user.admin_role:
        return user.admin_role.level <= 2  # Simplified permission check
    return False

@register.filter
def creator_name(content):
    """Get the username of the content creator or a default value if none exists."""
    if content and hasattr(content, 'creator') and content.creator:
        return content.creator.username
    return "No creator"

@register.filter
def creator_id(content):
    """Get the ID of the content creator or None if no creator exists."""
    if content and hasattr(content, 'creator') and content.creator:
        return content.creator.id
    return None

@register.filter
def moderation_badge_class(status):
    """
    Return the appropriate Bootstrap badge color class based on moderation status.
    
    Usage: {{ video.moderation_status|moderation_badge_class }}
    """
    status_classes = {
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'flagged': 'danger',
        'in_review': 'info'
    }
    return status_classes.get(status.lower(), 'secondary') 