from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def format_view_count(count):
    """
    Format view count to display in a user-friendly way
    Example: 1200 => 1.2K, 1500000 => 1.5M
    """
    try:
        count_num = int(count)
        if count_num < 1000:
            return str(count_num)
        elif count_num < 1000000:
            return f"{count_num/1000:.1f}K".replace('.0K', 'K')
        else:
            return f"{count_num/1000000:.1f}M".replace('.0M', 'M')
    except (ValueError, TypeError):
        return "0" 