from django import forms

from core.app_registry import registry
from core.rbac.roles import Role


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
        self._app_keys = []
        for app in registry.all():
            field_name = self._field_name(app.key)
            self._app_keys.append(app.key)
            self.fields[field_name] = forms.BooleanField(
                label=app.name,
                required=False,
                initial=self._initial_for_app(app.key),
            )

    @staticmethod
    def _field_name(app_key: str) -> str:
        return f"app_access_{app_key}"

    def _initial_for_app(self, app_key: str) -> bool:
        if not self.target_user:
            return False
        field_name = self._field_name(app_key)
        if self.data and field_name in self.data:
            return self.data.get(field_name, "") == "on"
        from core.app_registry.services import app_access_permissions

        for entry in app_access_permissions(self.target_user):
            if entry["app"].key == app_key:
                return entry["granted"]
        return False

    @property
    def app_fields(self):
        """Return the application access checkboxes for the template."""
        return [self[self._field_name(app_key)] for app_key in self._app_keys]

    def get_selected_app_keys(self) -> set[str]:
        """Return the set of application keys whose access box is checked."""
        selected = set()
        for app_key in self._app_keys:
            if self.cleaned_data.get(self._field_name(app_key)):
                selected.add(app_key)
        return selected
