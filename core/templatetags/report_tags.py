from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag('core/report_button.html')
def report_button(content_type, object_id, content_title=None):
    """
    Renders a report button for the specified content.
    
    Args:
        content_type: The type of content (video, image, blog)
        object_id: The ID of the content object
        content_title: Optional title of the content
    
    Returns:
        Context for the report button template
    """
    report_url = reverse('core:report_content', kwargs={
        'content_type': content_type,
        'object_id': object_id
    })
    
    return {
        'content_type': content_type,
        'object_id': object_id,
        'content_title': content_title,
        'report_url': report_url
    } 