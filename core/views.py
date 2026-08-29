"""Platform-level views."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.app_registry.services import apps_for_user
from core.navigation.registry import get_nav_items
from core.rbac.services import get_user_role


@login_required(login_url="/login/")
def dashboard(request):
    """Landing page for authenticated users."""
    nav_items = get_nav_items(request)
    app_cards = apps_for_user(request.user)
    role = get_user_role(request.user)
    stats = {
        "applications": len(app_cards),
        "current_user": request.user.get_full_name() or request.user.username,
        "role": role.value if role else "—",
    }
    return render(
        request,
        "pages/dashboard.html",
        {
            "page_title": "Internal Tools",
            "page_description": "Platform dashboard",
            "nav_items": nav_items,
            "app_cards": app_cards,
            "stats": stats,
        },
    )


def permission_denied(request, exception=None):
    """Render a platform-style 403 page."""
    return render(
        request,
        "errors/403.html",
        {"page_title": "Access Denied"},
        status=403,
    )
