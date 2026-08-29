from django.shortcuts import render

from apps.demo_one.services.data import DemoOneDataService
from core.navigation.registry import get_nav_items


def index(request):
    """Placeholder view for Demo App One."""
    items = DemoOneDataService.list_items()
    return render(
        request,
        "demo_one/index.html",
        {
            "page_title": "Demo App One",
            "page_description": (
                "This is a placeholder internal application. It demonstrates "
                "how business applications live inside the shared Internal Tools Platform."
            ),
            "nav_items": get_nav_items(request),
            "items": items,
        },
    )
