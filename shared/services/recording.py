"""Small domain-neutral helpers for recording common business mutations.

These helpers coordinate shared primitives (assignments, comments,
status history, audit logs) so business services do not repeat the same
low-level recording steps. They do NOT enforce transitions or business
rules; the app service remains in full control of permissions and logic.
"""

from shared.services.primitives import assignments, audit, comments, status_history


def record_status_change(
    obj,
    *,
    previous_status: str,
    new_status: str,
    actor,
    note: str = "",
    app_key: str,
    action: str,
    metadata: dict | None = None,
):
    """Record a status transition and corresponding audit event for ``obj``."""
    status_history.record(
        obj=obj,
        new_status=new_status,
        previous_status=previous_status,
        actor=actor,
        note=note,
    )
    audit.log(
        actor=actor,
        app_key=app_key,
        action=action,
        obj=obj,
        metadata=metadata or {},
    )


def record_assignment(obj, *, assigned_to, assigned_by, app_key: str, action: str):
    """Assign ``obj`` to ``assigned_to`` and record an audit event."""
    record = assignments.assign(
        obj=obj,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
    )
    audit.log(
        actor=assigned_by,
        app_key=app_key,
        action=action,
        obj=obj,
        metadata={
            "assigned_to": assigned_to.username,
            "assigned_by": assigned_by.username,
        },
    )
    return record


def record_note(obj, *, author, body: str, app_key: str, action: str):
    """Add a note to ``obj`` and record an audit event."""
    note = comments.add(obj=obj, author=author, body=body)
    audit.log(
        actor=author,
        app_key=app_key,
        action=action,
        obj=obj,
        metadata={"author": author.username},
    )
    return note
