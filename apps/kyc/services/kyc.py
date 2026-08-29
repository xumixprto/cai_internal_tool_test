"""KYC business service."""

from django.db import transaction

from apps.kyc.models.kyc import KYCApplication
from apps.kyc.providers.kyc_provider import LocalKYCProvider
from shared.services.activity import build_activity
from shared.services.primitives import assignments, audit, comments, status_history


class KYCServiceError(Exception):
    """Raised when a KYC business rule is violated."""


class KYCService:
    """Coordinates KYC case state changes, identity verification, and history."""

    def __init__(self, provider=None):
        self._provider = provider or LocalKYCProvider()

    @staticmethod
    def _terminal_statuses() -> tuple[str, str]:
        return (KYCApplication.Status.APPROVED, KYCApplication.Status.REJECTED)

    def _validate_not_terminal(self, case):
        if case.status in self._terminal_statuses():
            display = case.get_status_display()
            raise KYCServiceError(f"KYC case is already {display.lower()}.")

    def _validate_transition(self, case, allowed):
        self._validate_not_terminal(case)
        if case.status not in allowed:
            display = case.get_status_display()
            raise KYCServiceError(
                f"Cannot perform this action while KYC case is {display.lower()}."
            )

    @staticmethod
    def _require_reason(reason: str, label: str = "reason"):
        if not reason or not reason.strip():
            raise KYCServiceError(f"A {label} is required.")

    def move_to_under_review(self, case, actor):
        """Move a pending or escalated case to under review."""
        self._validate_transition(
            case,
            (KYCApplication.Status.PENDING, KYCApplication.Status.ESCALATED),
        )
        previous_status = case.status
        with transaction.atomic():
            case.status = KYCApplication.Status.UNDER_REVIEW
            case.save()
            status_history.record(
                obj=case,
                new_status=KYCApplication.Status.UNDER_REVIEW,
                previous_status=previous_status,
                actor=actor,
                note="Review started",
            )
            audit.log(
                actor=actor,
                app_key="kyc",
                action="kyc.review_started",
                obj=case,
                metadata={"previous_status": previous_status},
            )
        return case

    def approve(self, case, actor):
        """Approve a KYC case after provider verification succeeds."""
        self._validate_transition(case, (KYCApplication.Status.UNDER_REVIEW,))
        verification = self._provider.verify_identity(case)

        if not verification.get("identity_match") or not verification.get("document_verified"):
            raise KYCServiceError("Identity verification failed.")
        if verification.get("screening_result") == "flagged":
            raise KYCServiceError("Case has screening flags and must be escalated or rejected.")

        previous_status = case.status
        with transaction.atomic():
            case.provider_verification_status = KYCApplication.ProviderVerificationStatus.VERIFIED
            case.screening_flags = verification.get("screening_flags", "")
            case.provider_reference = verification.get("provider_reference", "")
            case.status = KYCApplication.Status.APPROVED
            case.save()
            status_history.record(
                obj=case,
                new_status=KYCApplication.Status.APPROVED,
                previous_status=previous_status,
                actor=actor,
                note="KYC approved",
            )
            audit.log(
                actor=actor,
                app_key="kyc",
                action="kyc.approved",
                obj=case,
                metadata={
                    "customer_name": case.customer_name,
                    "provider_reference": case.provider_reference,
                    "risk_level": case.risk_level,
                    "screening_flags": case.screening_flags,
                },
            )
        return case

    def reject(self, case, actor, reason: str):
        """Reject a KYC case, requiring a reason."""
        self._require_reason(reason, "rejection reason")
        self._validate_transition(
            case,
            (
                KYCApplication.Status.PENDING,
                KYCApplication.Status.UNDER_REVIEW,
            ),
        )
        previous_status = case.status
        with transaction.atomic():
            case.status = KYCApplication.Status.REJECTED
            case.rejection_reason = reason
            case.save()
            status_history.record(
                obj=case,
                new_status=KYCApplication.Status.REJECTED,
                previous_status=previous_status,
                actor=actor,
                note=reason,
            )
            audit.log(
                actor=actor,
                app_key="kyc",
                action="kyc.rejected",
                obj=case,
                metadata={"reason": reason},
            )
        return case

    def escalate(self, case, actor, reason: str):
        """Escalate a KYC case, requiring a reason."""
        self._require_reason(reason, "escalation reason")
        self._validate_transition(
            case,
            (KYCApplication.Status.UNDER_REVIEW,),
        )
        previous_status = case.status
        with transaction.atomic():
            case.status = KYCApplication.Status.ESCALATED
            case.save()
            status_history.record(
                obj=case,
                new_status=KYCApplication.Status.ESCALATED,
                previous_status=previous_status,
                actor=actor,
                note=reason,
            )
            audit.log(
                actor=actor,
                app_key="kyc",
                action="kyc.escalated",
                obj=case,
                metadata={"reason": reason},
            )
        return case

    def assign(self, case, assigned_to, assigned_by):
        """Assign a KYC case to a user and record an audit event."""
        with transaction.atomic():
            record = assignments.assign(
                obj=case,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
            )
            audit.log(
                actor=assigned_by,
                app_key="kyc",
                action="kyc.assigned",
                obj=case,
                metadata={
                    "assigned_to": assigned_to.username,
                    "assigned_by": assigned_by.username,
                },
            )
        return record

    def add_note(self, case, author, body: str):
        """Add an internal note to a KYC case."""
        if not body or not body.strip():
            raise KYCServiceError("Note body is required.")
        with transaction.atomic():
            note = comments.add(obj=case, author=author, body=body)
            audit.log(
                actor=author,
                app_key="kyc",
                action="kyc.note_added",
                obj=case,
                metadata={"author": author.username},
            )
        return note

    def get_current_assignment(self, case):
        """Return the current assignment for the case, or None."""
        return assignments.current_for(case)

    def get_notes(self, case):
        """Return internal notes for the case."""
        return comments.for_object(case)

    def get_activity(self, case):
        """Return a chronological activity feed for the case."""
        return build_activity(
            case,
            submitted_message="Case submitted",
            status_display=dict(KYCApplication.Status.choices),
        )


kyc_service = KYCService()
