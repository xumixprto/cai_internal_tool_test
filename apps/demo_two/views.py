from django.shortcuts import render

from apps.demo_two.services.data import DemoTwoDataService
from core.navigation.registry import get_nav_items


def index(request):
    """Placeholder view for Demo App Two."""
    items = DemoTwoDataService.list_items()
    return render(
        request,
        "demo_two/index.html",
        {
            "page_title": "Demo App Two",
            "page_description": (
                "This is a second placeholder internal application to prove "
                "the platform supports multiple independent business apps."
            ),
            "nav_items": get_nav_items(request),
            "items": items,
        },
    )
