from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from core.rbac.services import can_access_app, can_perform_action


class AppAccessRequiredMixin:
    """Class-based view mixin requiring the application access permission."""

    app_key = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                settings.LOGIN_URL,
                "next",
            )
        if not can_access_app(request.user, self.app_key):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AppActionRequiredMixin:
    """Class-based view mixin requiring app access plus a specific action."""

    app_key = None
    action_key = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                settings.LOGIN_URL,
                "next",
            )
        if not can_perform_action(request.user, self.app_key, self.action_key):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
