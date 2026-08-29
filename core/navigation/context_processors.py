"""Template context processor that injects navigation into every request."""

from core.navigation.registry import get_nav_items


def navigation(request):
    """Add the platform navigation to template context."""
    return {"nav_items": get_nav_items(request)}
