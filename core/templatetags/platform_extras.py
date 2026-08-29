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


@register.filter(is_safe=True)
def add_class(field, css_class):
    """Render a Django form field widget with the given CSS class added."""
    attrs = field.field.widget.attrs or {}
    existing = attrs.get("class", "")
    attrs["class"] = f"{existing} {css_class}".strip()
    return field.as_widget(attrs=attrs)


@register.filter
def widget_class(field):
    """Return the widget class name for a Django form field."""
    return field.field.widget.__class__.__name__


@register.filter
def platform_role(user):
    """Return the platform role for a user."""
    role = get_user_role(user)
    return role.value if role else "—"
