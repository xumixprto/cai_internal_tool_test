"""Small services for shared backend primitives.

Services accept domain objects and set the generic object reference.  Callers
are responsible for wrapping multi-step business mutations in
``transaction.atomic()`` when consistency matters.
"""

from django.contrib.contenttypes.models import ContentType

from shared.models.primitives import (
    Assignment,
    AuditLog,
    Comment,
    StatusHistory,
)


def _content_type_for(obj):
    """Return the ContentType for an object without requiring a saved model."""
    return ContentType.objects.get_for_model(obj)


def _object_id(obj):
    """Return a string primary key suitable for a generic object reference."""
    return str(obj.pk)


class audit:
    """Convenience namespace for append-only audit logging."""

    @staticmethod
    def log(actor, app_key: str, action: str, obj, metadata: dict | None = None):
        """Create an audit record for ``obj``.

        ``metadata`` should contain only small, domain-specific primitive
        values.  Never pass full model instances, passwords, or secrets.
        """
        return AuditLog.objects.create(
            actor=actor,
            app_key=app_key,
            action=action,
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
            metadata=metadata or {},
        )

    @staticmethod
    def for_object(obj):
        """Return audit log entries for ``obj``."""
        return AuditLog.objects.filter(
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )


class comments:
    """Convenience namespace for attaching plain-text notes to objects."""

    @staticmethod
    def add(obj, author, body: str):
        """Add a comment to ``obj``."""
        return Comment.objects.create(
            author=author,
            body=body,
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )

    @staticmethod
    def for_object(obj):
        """Return comments for ``obj``."""
        return Comment.objects.filter(
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )


class assignments:
    """Convenience namespace for object assignment history."""

    @staticmethod
    def assign(obj, assigned_to, assigned_by=None):
        """Record a new assignment for ``obj`` and return it."""
        return Assignment.objects.create(
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )

    @staticmethod
    def current_for(obj):
        """Return the latest assignment for ``obj`` or None."""
        return (
            Assignment.objects.filter(
                content_type=_content_type_for(obj),
                object_id=_object_id(obj),
            )
            .select_related("assigned_to", "assigned_by")
            .first()
        )

    @staticmethod
    def history_for(obj):
        """Return the full assignment history for ``obj``."""
        return Assignment.objects.filter(
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )

    @staticmethod
    def latest_map_for(model_class, object_ids=None):
        """Return a dict mapping primary key to latest assignment for ``model_class``.

        The dict only contains numeric primary keys; string object identifiers
        are ignored.
        """
        ct = ContentType.objects.get_for_model(model_class)
        qs = Assignment.objects.filter(content_type=ct)
        if object_ids:
            qs = qs.filter(object_id__in=[str(pk) for pk in object_ids])
        latest_by_id = {}
        for record in qs.order_by("-assigned_at").select_related("assigned_to"):
            latest_by_id.setdefault(record.object_id, record)
        return {int(obj_id): record for obj_id, record in latest_by_id.items() if obj_id.isdigit()}

    @staticmethod
    def currently_assigned_to(model_class, user):
        """Return primary keys of ``model_class`` records currently assigned to ``user``."""
        mapping = assignments.latest_map_for(model_class)
        return [pk for pk, record in mapping.items() if record.assigned_to_id == user.id]


class status_history:
    """Convenience namespace for status transition records."""

    @staticmethod
    def record(
        obj,
        new_status: str,
        previous_status: str = "",
        actor=None,
        note: str = "",
    ):
        """Record a status transition for ``obj``.

        If ``previous_status`` is not supplied, the latest recorded status is
        used as the previous state.  Callers should pass the explicit previous
        status when it is known to avoid ambiguity.
        """
        if not previous_status:
            latest = status_history.latest_for(obj)
            if latest is not None:
                previous_status = latest.new_status

        return StatusHistory.objects.create(
            actor=actor,
            previous_status=previous_status,
            new_status=new_status,
            note=note,
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )

    @staticmethod
    def latest_for(obj):
        """Return the most recent status transition for ``obj`` or None."""
        return StatusHistory.objects.filter(
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        ).first()

    @staticmethod
    def for_object(obj):
        """Return status transition history for ``obj``."""
        return StatusHistory.objects.filter(
            content_type=_content_type_for(obj),
            object_id=_object_id(obj),
        )
