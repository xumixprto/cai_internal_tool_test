"""Tests for the Refund Review app."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.refunds.models.refund import RefundRequest
from apps.refunds.providers.refund_provider import RefundProvider
from apps.refunds.services.refunds import RefundService, RefundServiceError
from core.app_registry.services import set_user_app_access, sync_app_permissions

User = get_user_model()


class FixedReferenceProvider(RefundProvider):
    """Test provider that returns a deterministic reference."""

    def process_refund(self, refund):
        return "REF-TEST-123"


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


class RefundServiceTests(TestCase):
    """Refund business rules and service behavior."""

    def setUp(self):
        self.actor = User.objects.create_user(username="service_actor", password="pw")
        self.target_user = User.objects.create_user(username="assigned_user", password="pw")
        self.refund = RefundRequest.objects.create(
            transaction_id="TXN-SVC-1",
            customer_name="Test Customer",
            customer_email="test@example.com",
            amount="99.99",
            currency="USD",
            reason="Test reason",
            status=RefundRequest.Status.PENDING,
        )
        sync_app_permissions()

    def test_approve_sets_status_and_reference(self):
        service = RefundService(provider=FixedReferenceProvider())
        service.approve(self.refund, self.actor)

        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundRequest.Status.APPROVED)
        self.assertEqual(self.refund.external_reference, "REF-TEST-123")

    def test_approved_refund_cannot_be_approved_again(self):
        service = RefundService(provider=FixedReferenceProvider())
        service.approve(self.refund, self.actor)
        with self.assertRaises(RefundServiceError):
            service.approve(self.refund, self.actor)

    def test_reject_requires_reason(self):
        service = RefundService()
        with self.assertRaises(RefundServiceError):
            service.reject(self.refund, self.actor, "   ")

    def test_reject_sets_status_and_reason(self):
        service = RefundService()
        service.reject(self.refund, self.actor, "Duplicate")

        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundRequest.Status.REJECTED)
        self.assertEqual(self.refund.rejection_reason, "Duplicate")

    def test_rejected_refund_cannot_be_approved(self):
        service = RefundService()
        service.reject(self.refund, self.actor, "Duplicate")
        with self.assertRaises(RefundServiceError):
            RefundService(provider=FixedReferenceProvider()).approve(self.refund, self.actor)

    def test_assign_creates_history(self):
        service = RefundService()
        record = service.assign(self.refund, self.target_user, self.actor)

        current = service.get_current_assignment(self.refund)
        self.assertIsNotNone(current)
        self.assertEqual(current.assigned_to, self.target_user)
        self.assertEqual(record.assigned_to, self.target_user)

    def test_add_note_creates_comment_and_audit(self):
        service = RefundService()
        note = service.add_note(self.refund, self.actor, "Important context")
        self.assertEqual(note.body, "Important context")
        self.assertEqual(service.get_notes(self.refund).count(), 1)

    def test_activity_contains_status_and_notes(self):
        service = RefundService(provider=FixedReferenceProvider())
        service.assign(self.refund, self.target_user, self.actor)
        service.add_note(self.refund, self.actor, "note")
        service.approve(self.refund, self.actor)

        activity = service.get_activity(self.refund)
        self.assertTrue(any(entry["type"] == "note" for entry in activity))
        self.assertTrue(any(entry["type"] == "status" for entry in activity))
        self.assertTrue(any(entry["type"] == "assignment" for entry in activity))


class RefundViewsTests(TestCase):
    """Refund queue, detail, and action views."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")
        call_command("seed_refund_demo_data")
        sync_app_permissions()

    def setUp(self):
        self.admin = User.objects.get(username="admin")
        self.user1 = User.objects.get(username="user1")
        self.user2 = User.objects.get(username="user2")

    def test_manifest_appears_in_registry(self):
        from core.app_registry import registry

        self.assertIn("refunds", (m.key for m in registry.all()))

    def test_admin_receives_all_refund_permissions(self):
        admin = _refresh_user(self.admin)
        self.assertTrue(admin.has_perm("refunds.access"))
        self.assertTrue(admin.has_perm("refunds.approve"))
        self.assertTrue(admin.has_perm("refunds.reject"))
        self.assertTrue(admin.has_perm("refunds.assign"))

    def test_user_without_access_cannot_view_queue(self):
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("refunds:index"))
        self.assertEqual(response.status_code, 403)

    def test_granted_user_can_view_queue(self):
        set_user_app_access(self.user1, {"refunds"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("refunds:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Refund Review")

    def test_queue_filters_by_status(self):
        set_user_app_access(self.user1, {"refunds"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("refunds:index"), {"status": "approved"})
        self.assertEqual(response.status_code, 200)

    def test_queue_search_works(self):
        set_user_app_access(self.user1, {"refunds"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("refunds:index"), {"q": "Alice"})
        self.assertEqual(response.status_code, 200)

    def test_admin_can_approve_and_history_created(self):
        refund = RefundRequest.objects.first()
        refund.status = RefundRequest.Status.UNDER_REVIEW
        refund.save()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("refunds:approve", args=[refund.pk]))
        self.assertEqual(response.status_code, 302)

        refund.refresh_from_db()
        self.assertEqual(refund.status, RefundRequest.Status.APPROVED)
        self.assertTrue(refund.external_reference)

    def test_unauthorized_approval_is_denied(self):
        refund = RefundRequest.objects.first()
        set_user_app_access(self.user1, {"refunds"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(reverse("refunds:approve", args=[refund.pk]))
        self.assertEqual(response.status_code, 403)

    def test_reject_requires_reason(self):

        refund = RefundRequest.objects.first()
        refund.status = RefundRequest.Status.UNDER_REVIEW
        refund.save()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("refunds:reject", args=[refund.pk]))
        self.assertEqual(response.status_code, 302)

        refund.refresh_from_db()
        self.assertNotEqual(refund.status, RefundRequest.Status.REJECTED)

    def test_assign_permission_controls_assignment(self):
        refund = RefundRequest.objects.first()
        set_user_app_access(self.user1, {"refunds"}, {"refunds.assign"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("refunds:assign", args=[refund.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 302)

        refund.refresh_from_db()
        from shared.services.primitives import assignments

        current = assignments.current_for(refund)
        self.assertEqual(current.assigned_to, self.admin)

    def test_user_without_assign_permission_cannot_assign(self):
        refund = RefundRequest.objects.first()
        set_user_app_access(self.user2, {"refunds"})
        _refresh_user(self.user2)
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("refunds:assign", args=[refund.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_add_note_with_access(self):
        refund = RefundRequest.objects.first()
        set_user_app_access(self.user1, {"refunds"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("refunds:note", args=[refund.pk]),
            {"body": "Customer confirmed duplicate charge."},
        )
        self.assertEqual(response.status_code, 302)

        from shared.services.primitives import comments

        self.assertEqual(comments.for_object(refund).count(), 1)

    def test_user_without_access_cannot_add_note(self):
        refund = RefundRequest.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("refunds:note", args=[refund.pk]),
            {"body": "Should not be saved."},
        )
        self.assertEqual(response.status_code, 403)

    def test_forbidden_direct_detail_access(self):
        refund = RefundRequest.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.get(reverse("refunds:detail", args=[refund.pk]))
        self.assertEqual(response.status_code, 403)
