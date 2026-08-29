"""Vendor app forms."""

from django import forms
from django.contrib.auth import get_user_model

from apps.vendors.models.vendor import VendorApplication

User = get_user_model()


class VendorFilterForm(forms.Form):
    """Filters for the vendor approval queue."""

    status = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + list(VendorApplication.Status.choices),
    )
    risk = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + list(VendorApplication.RiskLevel.choices),
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search company, tax ID, country"}),
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label="—",
    )


class VendorNoteForm(forms.Form):
    """Add an operational note to a vendor application."""

    body = forms.CharField(
        label="Note",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
    )


class VendorRejectForm(forms.Form):
    """Reject a vendor application with a reason."""

    reason = forms.CharField(
        label="Rejection reason",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        max_length=500,
    )


class VendorRequestChangesForm(forms.Form):
    """Request changes on a vendor application."""

    reason = forms.CharField(
        label="Requested changes",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        max_length=500,
    )


class VendorAssignForm(forms.Form):
    """Assign a vendor application to an active platform user."""

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=True,
    )
