from functools import wraps

from django.core.exceptions import PermissionDenied

from core.rbac.services import can_access_app, is_admin


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
