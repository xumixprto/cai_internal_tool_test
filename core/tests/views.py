"""Test-only views for route authorization."""

from django.contrib.auth.decorators import login_required

from core.rbac.decorators import require_app_access


@login_required(login_url="/login/")
@require_app_access("test_app_one")
def test_one_index(request):
    """Test-only app view protected by app access."""
    from django.http import HttpResponse

    return HttpResponse("test app one")


@login_required(login_url="/login/")
@require_app_access("test_app_two")
def test_two_index(request):
    """Test-only app view protected by app access."""
    from django.http import HttpResponse

    return HttpResponse("test app two")
