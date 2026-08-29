"""Platform-level views."""

from django.shortcuts import render

from core.navigation.registry import get_nav_items


def dashboard(request):
    """Landing page for the Internal Tools Platform."""
    nav_items = get_nav_items(request)
    app_cards = [item for item in nav_items if item["key"] != "dashboard"]
    stats = {
        "applications": len(app_cards),
        "open_tasks": "—",
        "current_user": "Demo User",
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
