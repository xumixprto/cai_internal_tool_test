"""Typed manifest for Internal Tools Platform business applications."""

import re
from dataclasses import dataclass

KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _is_valid_key(value: str) -> bool:
    return bool(value and KEY_RE.match(value))


def _is_valid_permission(value: str) -> bool:
    if not value:
        return False
    parts = value.rsplit(".", 1)
    return len(parts) == 2 and _is_valid_key(parts[0]) and _is_valid_key(parts[1])


_URL_NAME_RE = re.compile(r"^[^:]+:[^:]+$")


def _is_valid_url_name(value: str) -> bool:
    return bool(value and _URL_NAME_RE.match(value))


def _label_from_key(key: str) -> str:
    return key.replace("_", " ").strip().title()


@dataclass(frozen=True)
class AppAction:
    """Action exposed by a business application."""

    key: str
    permission: str
    label: str
    order: int = 100

    def __post_init__(self):
        errors = []
        if not _is_valid_key(self.key):
            errors.append(f"action key '{self.key}' must match {KEY_RE.pattern}")
        if not self.label or not self.label.strip():
            errors.append("action label is required")
        if not _is_valid_permission(self.permission):
            errors.append(f"action permission '{self.permission}' must be <app>.<codename>")
        if errors:
            raise ValueError("; ".join(errors))


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
    actions: tuple[AppAction, ...] = ()
    order: int = 100

    def __post_init__(self):
        errors = []
        if not _is_valid_key(self.key):
            errors.append(f"key '{self.key}' must match {KEY_RE.pattern}")
        if not self.name or not self.name.strip():
            errors.append("name is required")
        if not self.description or not self.description.strip():
            errors.append("description is required")
        if not _is_valid_url_name(self.url_name):
            msg = (
                f"url_name '{self.url_name}' must be a namespaced "
                "URL reference (<namespace>:<name>)"
            )
            errors.append(msg)
        if self.access_permission != f"{self.key}.access":
            errors.append(
                f"access_permission '{self.access_permission}' must be '{self.key}.access'"
            )

        normalized_actions = self._normalize_actions(self.actions)
        for action in normalized_actions:
            if action.key == "access":
                errors.append(
                    "action key 'access' is reserved for the application access permission"
                )
            if not _is_valid_key(action.key):
                errors.append(f"action key '{action.key}' must match {KEY_RE.pattern}")
            if action.permission != f"{self.key}.{action.key}":
                errors.append(
                    f"action permission '{action.permission}' must be '{self.key}.{action.key}'"
                )
            if not action.label or not action.label.strip():
                errors.append(f"action label for '{action.key}' is required")

        if errors:
            raise ValueError("; ".join(errors))

        # Frozen dataclasses require object.__setattr__ to modify the instance.
        if normalized_actions is not self.actions:
            object.__setattr__(self, "actions", normalized_actions)

    @staticmethod
    def _normalize_actions(value):
        if not value:
            return ()
        if isinstance(value, AppAction):
            return (value,)
        if isinstance(value, dict):
            return tuple(
                AppAction(key=k, permission=p, label=_label_from_key(k)) for k, p in value.items()
            )
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                if isinstance(item, AppAction):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(
                        AppAction(
                            key=item["key"],
                            permission=item["permission"],
                            label=item.get("label", _label_from_key(item["key"])),
                            order=item.get("order", 100),
                        )
                    )
                else:
                    raise TypeError(f"Unsupported action value: {item!r}")
            return tuple(result)
        raise TypeError("actions must be a sequence of AppAction or a mapping")

    @property
    def access_codename(self) -> str:
        """Return the permission codename for the application's access permission."""
        return self.access_permission.rsplit(".", 1)[1]

    def get_action(self, key: str) -> AppAction:
        """Return the action with the given key."""
        for action in self.actions:
            if action.key == key:
                return action
        raise KeyError(f"No action '{key}' on app '{self.key}'")

    @property
    def actions_by_key(self) -> dict[str, AppAction]:
        """Return actions keyed by action key."""
        return {action.key: action for action in self.actions}
