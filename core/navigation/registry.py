"""Centralized navigation registry for the platform.

Navigation is intentionally simple in Milestone 1.  Each entry references a
URL name so the system remains compatible with a future App Registry that
will discover installed apps and permission-check their visibility.
"""

from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

NAV_ITEMS = [
    {
        "key": "dashboard",
        "name": "Dashboard",
        "url_name": "dashboard",
        "icon": "house",
    },
    {
        "key": "demo_one",
        "name": "Demo App One",
        "url_name": "demo_one:index",
        "icon": "collection",
    },
    {
        "key": "demo_two",
        "name": "Demo App Two",
        "url_name": "demo_two:index",
        "icon": "clipboard-data",
    },
]


def _current_url_name(request) -> str:
    """Return the current resolved URL name, including namespace if any."""
    match = getattr(request, "resolver_match", None)
    if not match:
        return ""
    namespace = match.namespace or ""
    url_name = match.url_name or ""
    if namespace and url_name:
        return f"{namespace}:{url_name}"
    return namespace or url_name


def get_nav_items(request=None):
    """Return navigation items with resolved URLs and active flags."""
    current = _current_url_name(request) if request else ""
    items = []
    for item in NAV_ITEMS:
        new_item = item.copy()
        try:
            new_item["url"] = reverse(item["url_name"])
        except NoReverseMatch:
            new_item["url"] = "#"
        new_item["active"] = item["url_name"] == current
        items.append(new_item)
    return items
