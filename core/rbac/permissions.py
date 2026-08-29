from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class PlatformPermission:
    """Platform-wide permission constants."""

    ACCESS_ADMIN = "core_authentication.access_admin"
    ACCESS_ADMIN_CODENAME = "access_admin"


def parse_permission(permission: str) -> tuple[str, str]:
    """Split a semantic permission string into (app_label, codename)."""
    if not permission or "." not in permission:
        raise ValueError(f"Permission '{permission}' must be <app>.<codename>")
    app_label, codename = permission.rsplit(".", 1)
    if not app_label or not codename:
        raise ValueError(f"Permission '{permission}' must be <app>.<codename>")
    return app_label, codename


def ensure_permission(permission: str, name: str | None = None) -> Permission:
    """Ensure a Permission exists for the given semantic identifier.

    Permissions are anchored to a synthetic ContentType named after the
    application so that identifiers such as `refunds.access` work with
    Django's standard `user.has_perm()` checks.
    """
    app_label, codename = parse_permission(permission)
    name = name or f"Can {codename}"

    ct, _ = ContentType.objects.get_or_create(
        app_label=app_label,
        model="permission",
    )

    perm, _ = Permission.objects.get_or_create(
        content_type=ct,
        codename=codename,
        defaults={"name": name},
    )

    if perm.name != name:
        perm.name = name
        perm.save(update_fields=["name"])

    return perm


def get_permission(permission: str) -> Permission:
    """Return an existing Permission for a semantic permission string."""
    app_label, codename = parse_permission(permission)
    return Permission.objects.get(
        content_type__app_label=app_label,
        codename=codename,
    )
