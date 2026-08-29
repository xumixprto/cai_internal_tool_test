"""Tests for shared backend primitives."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from shared.models.primitives import Assignment, AuditLog
from shared.services.primitives import (
    assignments,
    audit,
    comments,
    status_history,
)

User = get_user_model()


class TimestampedModelTests(TestCase):
    """TimestampedModel sets created_at and updated_at."""

    def test_audit_log_sets_timestamps(self):
        actor = User.objects.create_user(username="ts_user", password="pw")
        obj = User.objects.create_user(username="ts_obj", password="pw")
        log = audit.log(actor, "test_app", "create", obj, {"key": "value"})
        self.assertIsNotNone(log.created_at)
        self.assertIsNotNone(log.updated_at)


class AuditLogTests(TestCase):
    """Append-only audit log with generic object references."""

    def setUp(self):
        self.actor = User.objects.create_user(username="audit_actor", password="pw")
        self.obj = User.objects.create_user(username="audit_obj", password="pw")

    def test_audit_log_create_and_query(self):
        audit.log(
            self.actor,
            "test_app",
            "test.action",
            self.obj,
            {"amount": "100.00"},
        )
        logs = list(audit.for_object(self.obj))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].action, "test.action")
        self.assertEqual(logs[0].metadata, {"amount": "100.00"})

    def test_deleting_actor_does_not_delete_audit_history(self):
        log = audit.log(self.actor, "test_app", "delete", self.obj)
        self.actor.delete()
        log.refresh_from_db()
        self.assertIsNone(log.actor)
        self.assertIsNotNone(AuditLog.objects.get(pk=log.pk))


class CommentTests(TestCase):
    """Plain-text comments attached to any object."""

    def setUp(self):
        self.author = User.objects.create_user(username="comment_author", password="pw")
        self.obj = User.objects.create_user(username="comment_obj", password="pw")

    def test_comments_attach_and_retrieve(self):
        comments.add(self.obj, self.author, "First note.")
        comments.add(self.obj, self.author, "Second note.")
        results = list(comments.for_object(self.obj))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].body, "Second note.")


class AssignmentTests(TestCase):
    """Assignment history and current assignment lookup."""

    def setUp(self):
        self.assigned_to = User.objects.create_user(username="assigned_to", password="pw")
        self.assigned_by = User.objects.create_user(username="assigned_by", password="pw")
        self.obj = User.objects.create_user(username="assignment_obj", password="pw")

    def test_assignment_history_retained(self):
        assignments.assign(self.obj, self.assigned_to, self.assigned_by)
        self.assertEqual(Assignment.objects.count(), 1)

    def test_current_assignment_returns_latest(self):
        first = User.objects.create_user(username="first", password="pw")
        second = User.objects.create_user(username="second", password="pw")
        assignments.assign(self.obj, first)
        latest = assignments.assign(self.obj, second)
        current = assignments.current_for(self.obj)
        self.assertEqual(current, latest)
        self.assertEqual(current.assigned_to, second)


class StatusHistoryTests(TestCase):
    """Status transition history."""

    def setUp(self):
        self.actor = User.objects.create_user(username="status_actor", password="pw")
        self.obj = User.objects.create_user(username="status_obj", password="pw")

    def test_status_transitions_preserve_history(self):
        status_history.record(
            self.obj,
            new_status="Pending",
            actor=self.actor,
        )
        status_history.record(
            self.obj,
            new_status="Approved",
            previous_status="Pending",
            actor=self.actor,
            note="Manager approved",
        )
        history = list(status_history.for_object(self.obj))
        self.assertEqual(len(history), 2)
        latest = history[0]
        self.assertEqual(latest.new_status, "Approved")
        self.assertEqual(latest.previous_status, "Pending")
        self.assertEqual(latest.note, "Manager approved")

    def test_previous_status_defaults_to_latest_record(self):
        status_history.record(self.obj, new_status="Pending")
        status_history.record(self.obj, new_status="Approved")
        latest = status_history.latest_for(self.obj)
        self.assertEqual(latest.previous_status, "Pending")


class GenericObjectReferenceTests(TestCase):
    """Generic foreign keys accept objects from different apps."""

    def setUp(self):
        self.user = User.objects.create_user(username="generic_user", password="pw")
        self.domain_object = User.objects.create_user(username="domain_obj", password="pw")

    def test_comment_works_with_model_object(self):
        comment = comments.add(self.domain_object, self.user, "Generic note.")
        self.assertEqual(comment.content_object, self.domain_object)
        self.assertEqual(str(comment.object_id), str(self.domain_object.pk))
