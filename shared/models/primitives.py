"""Shared backend primitives for internal tools applications."""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from shared.models.base import TimestampedModel


class GenericObjectReference(models.Model):
    """Abstract reusable generic foreign key to any domain object.

    Subclasses must include the concrete fields below; Django copies the
    GenericForeignKey into each subclass.  Object IDs are stored as strings
    so UUID and integer primary keys both work.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]


class AuditLog(GenericObjectReference, TimestampedModel):
    """Append-only operational audit trail for a domain object."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    app_key = models.CharField(max_length=255, db_index=True)
    action = models.CharField(max_length=255, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["app_key", "action", "timestamp"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.app_key}.{self.action} ({self.timestamp})"


class Comment(GenericObjectReference, TimestampedModel):
    """Plain-text operational note attached to a domain object."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
    )
    body = models.TextField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-created_at"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"


class Assignment(GenericObjectReference, TimestampedModel):
    """Assignment history for a domain object.  The latest record is current."""

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_to",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_by",
    )
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-assigned_at"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["assigned_by"]),
        ]

    def __str__(self):
        return f"Assigned to {self.assigned_to} at {self.assigned_at}"


class StatusHistory(GenericObjectReference, TimestampedModel):
    """Status transition history for a domain object."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_changes",
    )
    previous_status = models.CharField(max_length=255, blank=True)
    new_status = models.CharField(max_length=255)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "-created_at"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self):
        return f"{self.previous_status} -> {self.new_status}"
