from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect


class PlatformLoginView(LoginView):
    """Login view using the platform login template."""

    template_name = "authentication/login.html"
    redirect_authenticated_user = True


def logout_view(request):
    """Log the current user out and redirect to the login page."""
    logout(request)
    return redirect("core_authentication:login")
