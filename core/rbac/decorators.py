from functools import wraps

from django.core.exceptions import PermissionDenied

from core.rbac.services import is_admin


def admin_required(view):
    """Raise PermissionDenied unless the user is a platform admin."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
