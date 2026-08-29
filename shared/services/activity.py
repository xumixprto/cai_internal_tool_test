"""Domain-neutral activity timeline builder for business objects.

Aggregates shared primitives (status history, audit logs, comments, assignments)
into a single chronological feed that business apps can render.

Business apps decide which events are relevant by choosing what to record in
each primitive; this helper only collects and formats them.
"""

from __future__ import annotations

from collections.abc import Callable

from shared.services.primitives import assignments, audit, comments, status_history


def _default_audit_label(action: str) -> str:
    return action.replace(".", " ").replace("_", " ").title()


def build_activity(
    obj,
    *,
    submitted_message: str | None = None,
    status_display: dict[str, str] | None = None,
    audit_label_for: Callable[[str], str] | None = None,
):
    """Build a chronological activity feed for ``obj`` from shared primitives.

    Args:
        obj: The domain object to build activity for.
        submitted_message: If provided, an initial "submitted" entry is added
            using ``obj.created_at`` as its timestamp.
        status_display: Mapping from raw status values to human-readable labels.
        audit_label_for: Optional callable that transforms an audit action key
            into a human-readable label. Defaults to title-cased action.

    Returns:
        A list of activity entries sorted newest first.
    """
    entries = []
    status_labels = status_display or {}
    label_for = audit_label_for or _default_audit_label

    if submitted_message:
        entries.append(
            {
                "type": "submitted",
                "timestamp": getattr(obj, "created_at"),
                "actor": None,
                "message": submitted_message,
            }
        )

    for record in status_history.for_object(obj):
        label = status_labels.get(record.new_status, record.new_status)
        entries.append(
            {
                "type": "status",
                "timestamp": record.created_at,
                "actor": record.actor,
                "message": f"Status changed to {label}",
                "note": record.note,
            }
        )

    for log in audit.for_object(obj):
        entries.append(
            {
                "type": "audit",
                "timestamp": log.timestamp,
                "actor": log.actor,
                "message": label_for(log.action),
                "metadata": log.metadata,
            }
        )

    for note in comments.for_object(obj):
        entries.append(
            {
                "type": "note",
                "timestamp": note.created_at,
                "actor": note.author,
                "message": note.body,
            }
        )

    for record in assignments.history_for(obj):
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
