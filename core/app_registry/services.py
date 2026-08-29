from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core.app_registry import registry
from core.rbac.permissions import PlatformPermission, ensure_permission, get_permission
from core.rbac.roles import Role

User = get_user_model()


def sync_app_permissions() -> None:
    """Ensure every permission declared in the App Registry exists.

    Creates ContentType and Permission objects for each application's access
    permission and action permissions, then grants all of them to the Admin
    group.  Idempotent.
    """
    admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)

    permission_ids = set()

    # Platform admin permission always belongs to the Admin group.
    admin_access = ensure_permission(
        PlatformPermission.ACCESS_ADMIN,
        name="Can access platform admin",
    )
    permission_ids.add(admin_access.id)

    for app in registry.all():
        access_perm = ensure_permission(
            app.access_permission,
            name=f"Can access {app.name}",
        )
        permission_ids.add(access_perm.id)

        for action in app.actions:
            action_perm = ensure_permission(
                action.permission,
                name=f"Can {action.label} {app.name}",
            )
            permission_ids.add(action_perm.id)

    admin_group.permissions.set(permission_ids)


def apps_for_user(user) -> list[dict]:
    """Return registry apps the user may access as serialized nav-item dicts."""
    if not user.is_authenticated:
        return []

    is_platform_admin = user.has_perm(PlatformPermission.ACCESS_ADMIN)

    from django.urls import reverse

    items = []
    for app in registry.all():
        if not is_platform_admin and not user.has_perm(app.access_permission):
            continue
        item = {
            "key": app.key,
            "name": app.name,
            "description": app.description,
            "url_name": app.url_name,
            "icon": app.icon or "app",
            "permission": app.access_permission,
        }
        try:
            item["url"] = reverse(app.url_name)
        except Exception:
            item["url"] = "#"
        items.append(item)

    return items


def app_access_permissions(user) -> list[dict]:
    """Return application access permission state for each registered app.

    Each entry has the app metadata and a ``granted`` boolean reflecting the
    user's explicit access permission.  Admins are shown as granted because
    role-level permissions give them access.
    """
    if not user.is_authenticated:
        return []

    is_platform_admin = user.has_perm(PlatformPermission.ACCESS_ADMIN)
    result = []
    for app in registry.all():
        if is_platform_admin:
            granted = True
        else:
            try:
                perm = get_permission(app.access_permission)
                granted = user.user_permissions.filter(pk=perm.id).exists()
            except Exception:
                granted = False
        result.append({"app": app, "granted": granted})
    return result


def get_app_access_permission_ids() -> set[int]:
    """Return the IDs of all registered app access permissions."""
    ids = set()
    for app in registry.all():
        try:
            perm = ensure_permission(app.access_permission)
            ids.add(perm.id)
        except Exception:
            continue
    return ids


def get_app_action_permission_ids() -> set[int]:
    """Return the IDs of all registered app action permissions."""
    ids = set()
    for app in registry.all():
        for action in app.actions:
            try:
                perm = ensure_permission(action.permission)
                ids.add(perm.id)
            except Exception:
                continue
    return ids


def get_all_managed_permission_ids() -> set[int]:
    """Return IDs for all app access and app action permissions."""
    return get_app_access_permission_ids() | get_app_action_permission_ids()


def set_user_app_access(
    user,
    app_keys: set[str],
    action_permissions: set[str] | None = None,
) -> None:
    """Set a user's application access and action permissions.

    Only permissions managed by the registry are changed.  Unrelated user
    permissions, role membership, and permissions for other apps are preserved.
    Action permissions for apps whose access is removed are kept but become
    ineffective because the action helper requires app access first.
    """
    if not user.is_authenticated:
        return

    action_permissions = action_permissions or set()
    app_keys = set(app_keys)

    app_access_ids = get_app_access_permission_ids()
    app_action_ids = get_app_action_permission_ids()
    managed_ids = app_access_ids | app_action_ids

    selected_ids = set()
    preserve_action_ids = set()
    for app in registry.all():
        if app.key in app_keys:
            perm = ensure_permission(app.access_permission)
            if perm.id is not None:
                selected_ids.add(perm.id)
        else:
            # Preserve action permissions for apps the user no longer has access
            # to so they can be restored if access is re-granted later.
            for action in app.actions:
                perm = ensure_permission(action.permission)
                if perm.id is not None:
                    preserve_action_ids.add(perm.id)

    for app in registry.all():
        for action in app.actions:
            if action.permission in action_permissions:
                perm = ensure_permission(action.permission)
                if perm.id is not None:
                    selected_ids.add(perm.id)

    existing_ids = set(user.user_permissions.values_list("pk", flat=True))
    unrelated_ids = existing_ids - managed_ids
    new_ids = unrelated_ids | selected_ids | preserve_action_ids

    user.user_permissions.set(new_ids)
    # Invalidate Django permission caches.
    user.refresh_from_db(fields=["user_permissions"])
    for attr in ("_perm_cache", "_group_perm_cache"):
        if hasattr(user, attr):
            delattr(user, attr)
