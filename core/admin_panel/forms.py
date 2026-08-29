from django import forms

from core.rbac.roles import Role


class UserAccessForm(forms.Form):
    """Edit a user's platform role and active status."""

    role = forms.ChoiceField(
        choices=[(role.value, role.value) for role in Role],
        required=True,
    )
    is_active = forms.BooleanField(
        label="Active",
        required=False,
    )
