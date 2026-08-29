from django.contrib.auth.models import Group

from core.rbac.permissions import PlatformPermission
from core.rbac.roles import Role

PROTECTED_ADMIN_USERNAME = "admin"


def get_user_role(user):
    """Return the platform Role for a user, or None."""
    if user.groups.filter(name=Role.ADMIN.value).exists():
        return Role.ADMIN
    if user.groups.filter(name=Role.USER.value).exists():
        return Role.USER
    return None


def is_admin(user):
    """Return True if the user has platform admin access."""
    if not user.is_authenticated:
        return False
    return user.has_perm(PlatformPermission.ACCESS_ADMIN)


def has_permission(user, permission):
    """Return True if the user holds the given permission string."""
    if not user.is_authenticated:
        return False
    return user.has_perm(permission)


# Alias matching the RBAC vocabulary used by business application code.
can = has_permission


def can_access_app(user, app_key):
    """Return True if the user may access the registered application."""
    if not user.is_authenticated:
        return False

    from core.app_registry import registry

    try:
        manifest = registry.get(app_key)
    except KeyError:
        return False

    return user.has_perm(manifest.access_permission)


def can_perform_action(user, app_key, action_key):
    """Return True if the user has app access and the action permission."""
    if not can_access_app(user, app_key):
        return False

    from core.app_registry import registry

    try:
        manifest = registry.get(app_key)
        action = manifest.get_action(action_key)
    except KeyError:
        return False

    return user.has_perm(action.permission)


def set_user_access(user, role, is_active):
    """Assign a single platform role and active status to a user."""
    target_group, _ = Group.objects.get_or_create(name=role.value)
    user.groups.clear()
    user.groups.add(target_group)
    user.is_active = is_active
    user.save()
    # Force Django to recompute permission caches after group changes.
    for attr in ("_perm_cache", "_group_perm_cache", "_user_perm_cache"):
        if hasattr(user, attr):
            delattr(user, attr)
