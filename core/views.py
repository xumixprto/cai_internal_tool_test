"""Platform-level views."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render

from core.app_registry.services import apps_for_user
from core.forms import SampleForm
from core.navigation.breadcrumbs import simple_breadcrumbs
from core.navigation.registry import get_nav_items
from core.rbac.services import get_user_role, is_admin


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


@login_required(login_url="/login/")
def components_showcase(request):
    """Developer-only visual showcase of shared UI primitives.

    Only available in ``DEBUG`` mode and only to platform administrators.
    """
    if not settings.DEBUG:
        from django.http import Http404

        raise Http404("Developer components page is only available in DEBUG mode.")
    if not is_admin(request.user):
        raise PermissionDenied

    sample_form = SampleForm()
    paginator = Paginator(list(range(1, 46)), 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    edit_link = '<a href="#" class="btn btn-sm btn-outline-primary">Edit</a>'

    status_options = [
        {"value": "", "label": "All"},
        {"value": "pending", "label": "Pending"},
        {"value": "approved", "label": "Approved"},
        {"value": "rejected", "label": "Rejected"},
    ]

    return render(
        request,
        "pages/dev_components.html",
        {
            "page_title": "Component Showcase",
            "nav_items": get_nav_items(request),
            "breadcrumbs": simple_breadcrumbs(
                "Component Showcase",
                {"label": "Developer", "url": ""},
            ),
            "sample_form": sample_form,
            "page_obj": page_obj,
            "status_options": status_options,
            "sample_options": status_options[1:],
            "table_headers": ["ID", "Name", "Status", "Date", ""],
            "table_rows": [
                ["#101", "Refund A", "Pending", "2024-01-15", edit_link],
                ["#102", "Refund B", "Approved", "2024-01-16", edit_link],
                ["#103", "Refund C", "Rejected", "2024-01-17", edit_link],
            ],
            "detail_rows": [
                {"label": "Request ID", "value": "#101"},
                {"label": "Amount", "value": "$120.00"},
                {"label": "Requested by", "value": "user1"},
                {"label": "Status", "value": "Pending"},
            ],
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
