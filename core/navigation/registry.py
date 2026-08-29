"""Centralized navigation registry for the platform.

Core platform entries (Dashboard, Admin) are declared here.  Business
application entries come from the App Registry and are filtered by RBAC.
"""

from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from core.app_registry.services import apps_for_user

CORE_NAV_ITEMS = [
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


def _with_url(item, current):
    """Resolve the URL and active state for a nav item dict."""
    new_item = item.copy()
    try:
        new_item["url"] = reverse(item["url_name"])
    except NoReverseMatch:
        new_item["url"] = "#"
    new_item["active"] = item["url_name"] == current
    return new_item


def get_nav_items(request=None):
    """Return navigation items with resolved URLs and active flags."""
    current = _current_url_name(request) if request else ""
    items = []

    # Dashboard is always first.
    for item in CORE_NAV_ITEMS:
        if item["key"] == "dashboard":
            items.append(_with_url(item, current))

    # Business applications from the registry.
    if request and request.user.is_authenticated:
        for app in apps_for_user(request.user):
            app_item = {
                "key": app["key"],
                "name": app["name"],
                "url_name": app["url_name"],
                "icon": app.get("icon", "app"),
                "permission": app["permission"],
            }
            items.append(_with_url(app_item, current))

    # Admin entry, visible only to admins.
    for item in CORE_NAV_ITEMS:
        if item["key"] == "admin" and _is_visible(item, request):
            items.append(_with_url(item, current))

    return items
