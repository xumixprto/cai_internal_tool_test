"""Vendor business service."""

from django.db import transaction

from apps.vendors.models.vendor import VendorApplication
from apps.vendors.providers.vendor_provider import LocalVendorProvider
from shared.services.primitives import assignments, audit, comments, status_history


class VendorServiceError(Exception):
    """Raised when a vendor business rule is violated."""


class VendorService:
    """Coordinates vendor application state changes, history, and provider calls."""

    def __init__(self, provider=None):
        self._provider = provider or LocalVendorProvider()

    @staticmethod
    def _terminal_statuses() -> tuple[str, str]:
        return (VendorApplication.Status.APPROVED, VendorApplication.Status.REJECTED)

    def _validate_not_terminal(self, vendor):
        if vendor.status in self._terminal_statuses():
            display = vendor.get_status_display()
            raise VendorServiceError(f"Vendor application is already {display.lower()}.")

    def _validate_transition(self, vendor, allowed):
        self._validate_not_terminal(vendor)
        if vendor.status not in allowed:
            display = vendor.get_status_display()
            raise VendorServiceError(
                f"Cannot perform this action while vendor application is {display.lower()}."
            )

    def move_to_under_review(self, vendor, actor):
        """Move a submitted or changes-requested application to under review."""
        self._validate_transition(
            vendor,
            (
                VendorApplication.Status.SUBMITTED,
                VendorApplication.Status.CHANGES_REQUESTED,
            ),
        )
        previous_status = vendor.status
        with transaction.atomic():
            vendor.status = VendorApplication.Status.UNDER_REVIEW
            vendor.save()
            status_history.record(
                obj=vendor,
                new_status=VendorApplication.Status.UNDER_REVIEW,
                previous_status=previous_status,
                actor=actor,
                note="Review started",
            )
            audit.log(
                actor=actor,
                app_key="vendors",
                action="vendor.review_started",
                obj=vendor,
                metadata={"previous_status": previous_status},
            )
        return vendor

    def approve(self, vendor, actor):
        """Approve a vendor application and record validation history."""
        self._validate_transition(vendor, (VendorApplication.Status.UNDER_REVIEW,))
        previous_status = vendor.status
        with transaction.atomic():
            validation = self._provider.validate_vendor(vendor)
            vendor.status = VendorApplication.Status.APPROVED
            vendor.save()
            status_history.record(
                obj=vendor,
                new_status=VendorApplication.Status.APPROVED,
                previous_status=previous_status,
                actor=actor,
                note="Vendor approved",
            )
            audit.log(
                actor=actor,
                app_key="vendors",
                action="vendor.approved",
                obj=vendor,
                metadata={
                    "company_name": vendor.company_name,
                    "validation_reference": validation.get("validation_reference"),
                    "risk_level": vendor.risk_level,
                },
            )
        return vendor

    def reject(self, vendor, actor, reason: str):
        """Reject a vendor application, requiring a reason."""
        if not reason or not reason.strip():
            raise VendorServiceError("A rejection reason is required.")
        self._validate_transition(
            vendor,
            (
                VendorApplication.Status.SUBMITTED,
                VendorApplication.Status.UNDER_REVIEW,
                VendorApplication.Status.CHANGES_REQUESTED,
            ),
        )
        previous_status = vendor.status
        with transaction.atomic():
            vendor.status = VendorApplication.Status.REJECTED
            vendor.save()
            status_history.record(
                obj=vendor,
                new_status=VendorApplication.Status.REJECTED,
                previous_status=previous_status,
                actor=actor,
                note=reason,
            )
            audit.log(
                actor=actor,
                app_key="vendors",
                action="vendor.rejected",
                obj=vendor,
                metadata={"reason": reason},
            )
        return vendor

    def request_changes(self, vendor, actor, reason: str):
        """Request changes on a vendor application, requiring a reason."""
        if not reason or not reason.strip():
            raise VendorServiceError("A reason for requested changes is required.")
        self._validate_transition(
            vendor,
            (
                VendorApplication.Status.SUBMITTED,
                VendorApplication.Status.UNDER_REVIEW,
            ),
        )
        previous_status = vendor.status
        with transaction.atomic():
            vendor.status = VendorApplication.Status.CHANGES_REQUESTED
            vendor.save()
            status_history.record(
                obj=vendor,
                new_status=VendorApplication.Status.CHANGES_REQUESTED,
                previous_status=previous_status,
                actor=actor,
                note=reason,
            )
            audit.log(
                actor=actor,
                app_key="vendors",
                action="vendor.changes_requested",
                obj=vendor,
                metadata={"reason": reason},
            )
        return vendor

    def assign(self, vendor, assigned_to, assigned_by):
        """Assign a vendor application to a user and record an audit event."""
        with transaction.atomic():
            record = assignments.assign(
                obj=vendor,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
            )
            audit.log(
                actor=assigned_by,
                app_key="vendors",
                action="vendor.assigned",
                obj=vendor,
                metadata={
                    "assigned_to": assigned_to.username,
                    "assigned_by": assigned_by.username,
                },
            )
        return record

    def add_note(self, vendor, author, body: str):
        """Add an operational note to a vendor application."""
        if not body or not body.strip():
            raise VendorServiceError("Note body is required.")
        with transaction.atomic():
            note = comments.add(obj=vendor, author=author, body=body)
            audit.log(
                actor=author,
                app_key="vendors",
                action="vendor.note_added",
                obj=vendor,
                metadata={"author": author.username},
            )
        return note

    def get_current_assignment(self, vendor):
        """Return the current assignment for the vendor, or None."""
        return assignments.current_for(vendor)

    def get_notes(self, vendor):
        """Return operational notes for the vendor application."""
        return comments.for_object(vendor)

    def get_activity(self, vendor):
        """Return a chronological activity feed for the vendor."""
        entries = [
            {
                "type": "submitted",
                "timestamp": vendor.created_at,
                "actor": None,
                "message": "Application submitted",
            }
        ]
        for record in status_history.for_object(vendor):
            entries.append(
                {
                    "type": "status",
                    "timestamp": record.created_at,
                    "actor": record.actor,
                    "message": f"Status changed to {record.new_status}",
                    "note": record.note,
                }
            )
        for log in audit.for_object(vendor):
            entries.append(
                {
                    "type": "audit",
                    "timestamp": log.timestamp,
                    "actor": log.actor,
                    "message": log.action.replace(".", " ").replace("_", " ").title(),
                    "metadata": log.metadata,
                }
            )
        for note in comments.for_object(vendor):
            entries.append(
                {
                    "type": "note",
                    "timestamp": note.created_at,
                    "actor": note.author,
                    "message": note.body,
                }
            )
        for record in assignments.history_for(vendor):
            entries.append(
                {
                    "type": "assignment",
                    "timestamp": record.assigned_at,
                    "actor": record.assigned_by,
                    "message": f"Assigned to {record.assigned_to}",
                }
            )
        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return entries


vendor_service = VendorService()
