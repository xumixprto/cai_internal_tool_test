"""Sample forms used for platform demonstrations and component showcases."""

from django import forms


class SampleForm(forms.Form):
    """A representative form used to exercise shared form components."""

    name = forms.CharField(label="Name", max_length=100, help_text="Enter your full name.")
    email = forms.EmailField(label="Email", required=False)
    role = forms.ChoiceField(
        label="Role",
        choices=[("", "—"), ("admin", "Admin"), ("user", "User")],
        required=False,
    )
    notes = forms.CharField(
        label="Notes",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="Optional notes.",
    )
    due_date = forms.DateField(
        label="Due date",
        widget=forms.DateInput(attrs={"type": "date"}),
        required=False,
    )
    is_active = forms.BooleanField(label="Active account", required=False)
