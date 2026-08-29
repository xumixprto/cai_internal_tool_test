"""Refund app forms."""

from django import forms
from django.contrib.auth import get_user_model

from apps.refunds.models.refund import RefundRequest

User = get_user_model()


class RefundFilterForm(forms.Form):
    """Filters for the refund review queue."""

    status = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + list(RefundRequest.Status.choices),
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search customer, transaction, reason"}),
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label="—",
    )


class RefundNoteForm(forms.Form):
    """Add an operational note to a refund."""

    body = forms.CharField(
        label="Note",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
    )


class RefundRejectForm(forms.Form):
    """Reject a refund with a reason."""

    reason = forms.CharField(
        label="Rejection reason",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=True,
        max_length=500,
    )


class RefundAssignForm(forms.Form):
    """Assign a refund to an active platform user."""

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=True,
    )
