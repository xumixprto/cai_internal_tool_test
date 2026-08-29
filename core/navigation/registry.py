"""Centralized navigation registry for the platform.

Navigation entries use URL names so the system remains compatible with a future
App Registry.  Items may declare a permission; only users with that permission
see the entry.
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
        "key": "admin",
        "name": "Admin",
        "url_name": "core_admin_panel:index",
        "icon": "shield-lock",
        "permission": "core_authentication.access_admin",
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


def _is_visible(item, request):
    """Return True if the current user may see this navigation item."""
    permission = item.get("permission")
    if not permission:
        return True
    if not request or not request.user.is_authenticated:
        return False
    return request.user.has_perm(permission)


def get_nav_items(request=None):
    """Return navigation items with resolved URLs and active flags."""
    current = _current_url_name(request) if request else ""
    items = []
    for item in NAV_ITEMS:
        if not _is_visible(item, request):
            continue
        new_item = item.copy()
        try:
            new_item["url"] = reverse(item["url_name"])
        except NoReverseMatch:
            new_item["url"] = "#"
        new_item["active"] = item["url_name"] == current
        items.append(new_item)
    return items
