from django import forms

from core.app_registry import registry
from core.rbac.permissions import get_permission
from core.rbac.roles import Role
from core.rbac.services import is_admin


class UserAccessForm(forms.Form):
    """Edit a user's platform role, active status, and application access."""

    role = forms.ChoiceField(
        choices=[(role.value, role.value) for role in Role],
        required=True,
    )
    is_active = forms.BooleanField(
        label="Active",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.target_user = kwargs.pop("target_user", None)
        super().__init__(*args, **kwargs)
        self._apps = list(registry.all())
        self._action_map = {}  # field_name -> action permission string

        for app in self._apps:
            access_field_name = self._access_field_name(app.key)
            self.fields[access_field_name] = forms.BooleanField(
                label=app.name,
                required=False,
                initial=self._initial_access(app.key),
            )

            for action in app.actions:
                action_field_name = self._action_field_name(app.key, action.key)
                self._action_map[action_field_name] = action.permission
                self.fields[action_field_name] = forms.BooleanField(
                    label=action.label,
                    required=False,
                    initial=self._initial_action(action.permission),
                )

    @staticmethod
    def _access_field_name(app_key: str) -> str:
        return f"app_access_{app_key}"

    @staticmethod
    def _action_field_name(app_key: str, action_key: str) -> str:
        return f"app_action_{app_key}_{action_key}"

    def _is_post(self) -> bool:
        return bool(self.data and self.data.get("role"))

    def _field_value(self, field_name: str) -> bool:
        if self._is_post():
            return self.data.get(field_name, "") == "on"
        return self.fields[field_name].initial or False

    def _initial_access(self, app_key: str) -> bool:
        if not self.target_user:
            return False
        field_name = self._access_field_name(app_key)
        if self._is_post():
            return self.data.get(field_name, "") == "on"
        from core.app_registry.services import app_access_permissions

        for entry in app_access_permissions(self.target_user):
            if entry["app"].key == app_key:
                return entry["granted"]
        return False

    def _initial_action(self, permission: str) -> bool:
        if not self.target_user:
            return False
        if is_admin(self.target_user):
            return True
        try:
            perm = get_permission(permission)
        except Exception:
            return False
        return self.target_user.user_permissions.filter(pk=perm.id).exists()

    @property
    def app_groups(self):
        """Return app/access/action groups for the template."""
        groups = []
        for app in self._apps:
            access_field = self[self._access_field_name(app.key)]
            action_fields = [
                self[self._action_field_name(app.key, action.key)] for action in app.actions
            ]
            groups.append(
                {
                    "app": app,
                    "access": access_field,
                    "actions": action_fields,
                }
            )
        return groups

    def get_selected_app_keys(self) -> set[str]:
        """Return the set of application keys whose access box is checked."""
        selected = set()
        for app in self._apps:
            field_name = self._access_field_name(app.key)
            if self.cleaned_data.get(field_name):
                selected.add(app.key)
        return selected

    def get_selected_action_permissions(self) -> set[str]:
        """Return the permission strings for checked action boxes."""
        selected = set()
        for field_name, permission in self._action_map.items():
            if self.cleaned_data.get(field_name):
                selected.add(permission)
        return selected
