from django import template
from django.utils.safestring import mark_safe

register = template.Library()

BADGE_STYLES = {
    "Pending": "warning",
    "Complete": "success",
    "Open": "primary",
    "Closed": "secondary",
    "Approved": "success",
    "Rejected": "danger",
    "In Progress": "info",
}


@register.filter(is_safe=True)
def status_badge(status):
    """Render a Bootstrap badge for a status string."""
    style = BADGE_STYLES.get(str(status), "secondary")
    return mark_safe(f'<span class="badge rounded-pill bg-{style}">{status}</span>')
