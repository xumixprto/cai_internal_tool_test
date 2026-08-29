"""Test-only views for route authorization."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views import View

from core.rbac.decorators import (
    require_app_access,
    require_app_action,
)
from core.rbac.mixins import AppAccessRequiredMixin, AppActionRequiredMixin


@login_required(login_url="/login/")
@require_app_access("test_app_one")
def test_one_index(request):
    """Test-only app view protected by app access."""
    return HttpResponse("test app one")


@login_required(login_url="/login/")
@require_app_access("test_app_two")
def test_two_index(request):
    """Test-only app view protected by app access."""
    return HttpResponse("test app two")


@login_required(login_url="/login/")
@require_app_action("test_app_one", "approve")
def test_one_approve(request):
    """Test-only action-level view."""
    return HttpResponse("approved")


class TestOneListView(AppAccessRequiredMixin, View):
    """Class-based view protected by app access."""

    app_key = "test_app_one"

    def get(self, request, *args, **kwargs):
        return HttpResponse("cbv list")


class TestOneRejectView(AppActionRequiredMixin, View):
    """Class-based view protected by app access and reject action."""

    app_key = "test_app_one"
    action_key = "reject"

    def get(self, request, *args, **kwargs):
        return HttpResponse("cbv reject")
