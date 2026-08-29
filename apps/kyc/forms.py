"""KYC app forms."""

from django import forms
from django.contrib.auth import get_user_model

from apps.kyc.models.kyc import KYCApplication

User = get_user_model()


class KYCFilterForm(forms.Form):
    """Filters for the KYC review queue."""

    status = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + list(KYCApplication.Status.choices),
    )
    risk = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + list(KYCApplication.RiskLevel.choices),
    )
    verification = forms.ChoiceField(
        required=False,
        label="Verification",
        choices=[("", "—")] + list(KYCApplication.ProviderVerificationStatus.choices),
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search customer, ID, country, document"}),
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label="—",
    )


class KYCNoteForm(forms.Form):
    """Add an internal note to a KYC case."""

    body = forms.CharField(
        label="Note",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
    )


class KYCRejectForm(forms.Form):
    """Reject a KYC case with a reason."""

    reason = forms.CharField(
        label="Rejection reason",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        max_length=500,
    )


class KYCEscalateForm(forms.Form):
    """Escalate a KYC case with a reason."""

    reason = forms.CharField(
        label="Escalation reason",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        max_length=500,
    )


class KYCAssignForm(forms.Form):
    """Assign a KYC case to an active platform user."""

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=True,
    )
