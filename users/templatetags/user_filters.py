from django import template

register = template.Library()

@register.filter
def filter_content_type(videos, content_type):
    """Filter videos by content_type."""
    return [video for video in videos if video.content_type == content_type] 