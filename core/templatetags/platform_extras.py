from django import template
from django.utils.safestring import mark_safe

from core.rbac.services import get_user_role

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


@register.filter
def platform_role(user):
    """Return the platform role for a user."""
    role = get_user_role(user)
    return role.value if role else "—"
