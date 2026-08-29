from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from core.rbac.services import can_access_app, can_perform_action, is_admin


def admin_required(view):
    """Raise PermissionDenied unless the user is a platform admin."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def require_app_access(app_key):
    """Raise PermissionDenied unless the user may access the given app."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not can_access_app(request.user, app_key):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def require_app_action(app_key, action_key):
    """Require the application access permission plus a specific action permission.

    Anonymous users are redirected to the login page.  Authenticated users
    without the required permissions receive HTTP 403.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    settings.LOGIN_URL,
                    "next",
                )
            if not can_perform_action(request.user, app_key, action_key):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
