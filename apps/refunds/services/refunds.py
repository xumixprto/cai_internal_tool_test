"""Refund business service."""

from django.db import transaction

from apps.refunds.models.refund import RefundRequest
from apps.refunds.providers.refund_provider import LocalRefundProvider
from shared.services.activity import build_activity
from shared.services.primitives import assignments, audit, comments, status_history


class RefundServiceError(Exception):
    """Raised when a refund business rule is violated."""


class RefundService:
    """Coordinates refund state changes, history, and provider calls."""

    def __init__(self, provider=None):
        self._provider = provider or LocalRefundProvider()

    @staticmethod
    def _terminal_statuses() -> tuple[str, str]:
        return (RefundRequest.Status.APPROVED, RefundRequest.Status.REJECTED)

    def _validate_transition(self, refund):
        if refund.status in self._terminal_statuses():
            raise RefundServiceError(f"Refund is already {refund.get_status_display().lower()}.")

    def approve(self, refund, actor):
        """Approve a refund and record status/audit history."""
        self._validate_transition(refund)
        previous_status = refund.status
        with transaction.atomic():
            refund.external_reference = self._provider.process_refund(refund)
            refund.status = RefundRequest.Status.APPROVED
            refund.save()
            status_history.record(
                obj=refund,
                new_status=RefundRequest.Status.APPROVED,
                previous_status=previous_status,
                actor=actor,
                note="Refund approved",
            )
            audit.log(
                actor=actor,
                app_key="refunds",
                action="refund.approved",
                obj=refund,
                metadata={
                    "amount": str(refund.amount),
                    "currency": refund.currency,
                    "external_reference": refund.external_reference,
                },
            )
        return refund

    def reject(self, refund, actor, reason: str):
        """Reject a refund, requiring a reason, and record history."""
        if not reason or not reason.strip():
            raise RefundServiceError("A rejection reason is required.")
        self._validate_transition(refund)
        previous_status = refund.status
        with transaction.atomic():
            refund.status = RefundRequest.Status.REJECTED
            refund.rejection_reason = reason
            refund.save()
            status_history.record(
                obj=refund,
                new_status=RefundRequest.Status.REJECTED,
                previous_status=previous_status,
                actor=actor,
                note=reason,
            )
            audit.log(
                actor=actor,
                app_key="refunds",
                action="refund.rejected",
                obj=refund,
                metadata={"reason": reason},
            )
        return refund

    def assign(self, refund, assigned_to, assigned_by):
        """Assign a refund to a user and record an audit event."""
        with transaction.atomic():
            record = assignments.assign(
                obj=refund,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
            )
            audit.log(
                actor=assigned_by,
                app_key="refunds",
                action="refund.assigned",
                obj=refund,
                metadata={
                    "assigned_to": assigned_to.username,
                    "assigned_by": assigned_by.username,
                },
            )
        return record

    def add_note(self, refund, author, body: str):
        """Add an operational note to a refund."""
        if not body or not body.strip():
            raise RefundServiceError("Note body is required.")
        with transaction.atomic():
            note = comments.add(obj=refund, author=author, body=body)
            audit.log(
                actor=author,
                app_key="refunds",
                action="refund.note_added",
                obj=refund,
                metadata={"author": author.username},
            )
        return note

    def get_current_assignment(self, refund):
        """Return the current assignment for the refund, or None."""
        return assignments.current_for(refund)

    def get_notes(self, refund):
        """Return operational notes for the refund."""
        return comments.for_object(refund)

    def get_activity(self, refund):
        """Return a chronological activity feed for the refund."""
        return build_activity(
            refund,
            status_display=dict(RefundRequest.Status.choices),
        )


refund_service = RefundService()
