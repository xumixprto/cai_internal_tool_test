"""Typed manifest for Internal Tools Platform business applications."""

import re
from dataclasses import dataclass, field

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _is_valid_key(value: str) -> bool:
    return bool(value and KEY_RE.match(value))


def _is_valid_permission(value: str) -> bool:
    if not value:
        return False
    parts = value.rsplit(".", 1)
    return len(parts) == 2 and _is_valid_key(parts[0]) and _is_valid_key(parts[1])


@dataclass(frozen=True)
class AppManifest:
    """Platform metadata for a business application.

    Application code declares a manifest and registers it from its
    AppConfig.ready() method.  The registry keeps the metadata in memory
    and navigation, dashboard, and authorization helpers consume it.
    """

    key: str
    name: str
    description: str
    url_name: str
    access_permission: str
    icon: str = "app"
    actions: dict[str, str] = field(default_factory=dict)
    order: int = 100

    def __post_init__(self):
        errors = []
        if not _is_valid_key(self.key):
            errors.append(f"key '{self.key}' must match {KEY_RE.pattern}")
        if not self.name or not self.name.strip():
            errors.append("name is required")
        if not self.description or not self.description.strip():
            errors.append("description is required")
        if not self.url_name or not self.url_name.strip():
            errors.append("url_name is required")
        if not _is_valid_permission(self.access_permission):
            errors.append(f"access_permission '{self.access_permission}' must be <app>.<codename>")

        for action, permission in (self.actions or {}).items():
            if not _is_valid_key(action):
                errors.append(f"action name '{action}' must match {KEY_RE.pattern}")
            if not _is_valid_permission(permission):
                errors.append(f"action permission '{permission}' must be <app>.<codename>")

        if errors:
            raise ValueError("; ".join(errors))

    @property
    def access_codename(self) -> str:
        """Return the permission codename for the application's access permission."""
        return self.access_permission.rsplit(".", 1)[1]
