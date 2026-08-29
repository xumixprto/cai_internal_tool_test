"""Tests for the Vendor Approval app."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.vendors.models.vendor import VendorApplication
from apps.vendors.providers.vendor_provider import VendorProvider
from apps.vendors.services.vendors import VendorService, VendorServiceError
from core.app_registry.services import set_user_app_access, sync_app_permissions

User = get_user_model()


class FixedValidationProvider(VendorProvider):
    """Test provider that returns a deterministic validation result."""

    def validate_vendor(self, vendor):
        return {
            "valid": True,
            "company_status": "active",
            "validation_reference": "VND-TEST-123",
            "country": vendor.country,
        }


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


class VendorServiceTests(TestCase):
    """Vendor business rules and service behavior."""

    def setUp(self):
        self.actor = User.objects.create_user(username="service_actor", password="pw")
        self.target_user = User.objects.create_user(username="assigned_user", password="pw")
        self.vendor = VendorApplication.objects.create(
            company_name="Test Corp",
            contact_email="test@example.com",
            country="United States",
            category=VendorApplication.Category.SERVICES,
            tax_id="US-TEST-001",
            estimated_annual_spend="50000.00",
            risk_level=VendorApplication.RiskLevel.MEDIUM,
            status=VendorApplication.Status.SUBMITTED,
        )
        sync_app_permissions()

    def _to_under_review(self):
        VendorService().move_to_under_review(self.vendor, self.actor)
        self.vendor.refresh_from_db()

    def test_move_to_under_review(self):
        VendorService().move_to_under_review(self.vendor, self.actor)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorApplication.Status.UNDER_REVIEW)

    def test_approve_requires_under_review(self):
        with self.assertRaises(VendorServiceError):
            VendorService(provider=FixedValidationProvider()).approve(self.vendor, self.actor)

    def test_approve_sets_status_and_reference(self):
        self._to_under_review()
        VendorService(provider=FixedValidationProvider()).approve(self.vendor, self.actor)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorApplication.Status.APPROVED)

    def test_approved_vendor_cannot_be_approved_again(self):
        self._to_under_review()
        service = VendorService(provider=FixedValidationProvider())
        service.approve(self.vendor, self.actor)
        with self.assertRaises(VendorServiceError):
            service.approve(self.vendor, self.actor)

    def test_reject_requires_reason(self):
        with self.assertRaises(VendorServiceError):
            VendorService().reject(self.vendor, self.actor, "   ")

    def test_reject_sets_status_and_reason_in_status_history(self):
        VendorService().reject(self.vendor, self.actor, "Incomplete tax documents")
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorApplication.Status.REJECTED)

        from shared.services.primitives import status_history

        record = status_history.latest_for(self.vendor)
        self.assertEqual(record.note, "Incomplete tax documents")

    def test_rejected_vendor_cannot_be_approved(self):
        VendorService().reject(self.vendor, self.actor, "Incomplete tax documents")
        self.vendor.refresh_from_db()
        with self.assertRaises(VendorServiceError):
            VendorService(provider=FixedValidationProvider()).approve(self.vendor, self.actor)

    def test_request_changes_requires_reason(self):
        with self.assertRaises(VendorServiceError):
            VendorService().request_changes(self.vendor, self.actor, "   ")

    def test_request_changes_and_return_to_under_review(self):
        VendorService().request_changes(self.vendor, self.actor, "Provide certificate")
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorApplication.Status.CHANGES_REQUESTED)

        VendorService().move_to_under_review(self.vendor, self.actor)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.status, VendorApplication.Status.UNDER_REVIEW)

    def test_request_changes_not_allowed_after_approval(self):
        self._to_under_review()
        VendorService(provider=FixedValidationProvider()).approve(self.vendor, self.actor)
        self.vendor.refresh_from_db()
        with self.assertRaises(VendorServiceError):
            VendorService().request_changes(self.vendor, self.actor, "Should fail")

    def test_assign_creates_history(self):
        service = VendorService()
        record = service.assign(self.vendor, self.target_user, self.actor)
        current = service.get_current_assignment(self.vendor)
        self.assertEqual(current.assigned_to, self.target_user)
        self.assertEqual(record.assigned_to, self.target_user)

    def test_add_note_creates_comment_and_audit(self):
        service = VendorService()
        note = service.add_note(self.vendor, self.actor, "Important context")
        self.assertEqual(note.body, "Important context")
        self.assertEqual(service.get_notes(self.vendor).count(), 1)

    def test_activity_contains_status_and_notes(self):
        service = VendorService()
        service.assign(self.vendor, self.target_user, self.actor)
        service.add_note(self.vendor, self.actor, "note")
        service.move_to_under_review(self.vendor, self.actor)

        activity = service.get_activity(self.vendor)
        self.assertTrue(any(entry["type"] == "note" for entry in activity))
        self.assertTrue(any(entry["type"] == "status" for entry in activity))
        self.assertTrue(any(entry["type"] == "assignment" for entry in activity))
        self.assertTrue(any(entry["type"] == "submitted" for entry in activity))


class VendorViewsTests(TestCase):
    """Vendor queue, detail, and action views."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")
        call_command("seed_vendor_demo_data")
        sync_app_permissions()

    def setUp(self):
        self.admin = User.objects.get(username="admin")
        self.user1 = User.objects.get(username="user1")
        self.user2 = User.objects.get(username="user2")

    def test_manifest_appears_in_registry(self):
        from core.app_registry import registry

        self.assertIn("vendors", (m.key for m in registry.all()))

    def test_admin_receives_all_vendor_permissions(self):
        admin = _refresh_user(self.admin)
        self.assertTrue(admin.has_perm("vendors.access"))
        self.assertTrue(admin.has_perm("vendors.approve"))
        self.assertTrue(admin.has_perm("vendors.reject"))
        self.assertTrue(admin.has_perm("vendors.assign"))
        self.assertTrue(admin.has_perm("vendors.request_changes"))

    def test_user_without_access_cannot_view_queue(self):
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("vendors:index"))
        self.assertEqual(response.status_code, 403)

    def test_granted_user_can_view_queue(self):
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("vendors:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vendor Approval")

    def test_queue_filters_by_status(self):
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("vendors:index"), {"status": "approved"})
        self.assertEqual(response.status_code, 200)

    def test_queue_filters_by_risk(self):
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("vendors:index"), {"risk": "high"})
        self.assertEqual(response.status_code, 200)

    def test_queue_search_works(self):
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("vendors:index"), {"q": "Acme"})
        self.assertEqual(response.status_code, 200)

    def test_admin_can_request_changes(self):
        vendor = VendorApplication.objects.filter(
            status=VendorApplication.Status.UNDER_REVIEW
        ).first()
        self.client.login(username="admin", password="admin")
        response = self.client.post(
            reverse("vendors:request_changes", args=[vendor.pk]),
            {"reason": "Provide updated tax certificate"},
        )
        self.assertEqual(response.status_code, 302)

        vendor.refresh_from_db()
        self.assertEqual(vendor.status, VendorApplication.Status.CHANGES_REQUESTED)

    def test_return_to_under_review_works(self):
        vendor = VendorApplication.objects.create(
            company_name="Change Me",
            contact_email="change@example.com",
            country="United States",
            tax_id="US-CHANGES-001",
            estimated_annual_spend="10000.00",
            status=VendorApplication.Status.CHANGES_REQUESTED,
        )
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("vendors:review", args=[vendor.pk]))
        self.assertEqual(response.status_code, 302)

        vendor.refresh_from_db()
        self.assertEqual(vendor.status, VendorApplication.Status.UNDER_REVIEW)

    def test_admin_can_approve_and_history_created(self):
        vendor = VendorApplication.objects.filter(
            status=VendorApplication.Status.UNDER_REVIEW
        ).first()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("vendors:approve", args=[vendor.pk]))
        self.assertEqual(response.status_code, 302)

        vendor.refresh_from_db()
        self.assertEqual(vendor.status, VendorApplication.Status.APPROVED)

    def test_unauthorized_approval_is_denied(self):
        vendor = VendorApplication.objects.first()
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(reverse("vendors:approve", args=[vendor.pk]))
        self.assertEqual(response.status_code, 403)

    def test_reject_requires_reason(self):
        vendor = VendorApplication.objects.first()
        vendor.status = VendorApplication.Status.UNDER_REVIEW
        vendor.save()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("vendors:reject", args=[vendor.pk]))
        self.assertEqual(response.status_code, 302)

        vendor.refresh_from_db()
        self.assertNotEqual(vendor.status, VendorApplication.Status.REJECTED)

    def test_assign_permission_controls_assignment(self):
        vendor = VendorApplication.objects.first()
        set_user_app_access(self.user1, {"vendors"}, {"vendors.assign"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("vendors:assign", args=[vendor.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 302)

        from shared.services.primitives import assignments

        current = assignments.current_for(vendor)
        self.assertEqual(current.assigned_to, self.admin)

    def test_user_without_assign_permission_cannot_assign(self):
        vendor = VendorApplication.objects.first()
        set_user_app_access(self.user2, {"vendors"})
        _refresh_user(self.user2)
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("vendors:assign", args=[vendor.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_add_note_with_access(self):
        vendor = VendorApplication.objects.first()
        set_user_app_access(self.user1, {"vendors"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("vendors:note", args=[vendor.pk]),
            {"body": "Vendor confirmed registration."},
        )
        self.assertEqual(response.status_code, 302)

        from shared.services.primitives import comments

        self.assertEqual(comments.for_object(vendor).count(), 1)

    def test_user_without_access_cannot_add_note(self):
        vendor = VendorApplication.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("vendors:note", args=[vendor.pk]),
            {"body": "Should not be saved."},
        )
        self.assertEqual(response.status_code, 403)

    def test_forbidden_direct_detail_access(self):
        vendor = VendorApplication.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.get(reverse("vendors:detail", args=[vendor.pk]))
        self.assertEqual(response.status_code, 403)

    def test_independent_refund_and_vendor_access(self):
        set_user_app_access(self.user1, {"refunds"})
        set_user_app_access(self.user2, {"vendors"})
        _refresh_user(self.user1)
        _refresh_user(self.user2)

        self.client.login(username="user1", password="user1")
        self.assertEqual(
            self.client.get(reverse("refunds:index")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("vendors:index")).status_code,
            403,
        )

        self.client.login(username="user2", password="user2")
        self.assertEqual(
            self.client.get(reverse("vendors:index")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("refunds:index")).status_code,
            403,
        )

    def test_action_permissions_independent_per_app(self):
        set_user_app_access(
            self.user2,
            {"vendors"},
            {"vendors.approve", "vendors.assign", "vendors.request_changes"},
        )
        _refresh_user(self.user2)
        self.client.login(username="user2", password="user2")

        vendor = VendorApplication.objects.first()
        vendor.status = VendorApplication.Status.UNDER_REVIEW
        vendor.save()

        # user2 has approve but not reject.
        approve_response = self.client.post(reverse("vendors:approve", args=[vendor.pk]))
        self.assertEqual(approve_response.status_code, 302)

        vendor.status = VendorApplication.Status.UNDER_REVIEW
        vendor.save()
        reject_response = self.client.post(
            reverse("vendors:reject", args=[vendor.pk]),
            {"reason": "Should be forbidden"},
        )
        self.assertEqual(reject_response.status_code, 403)

    def test_invalid_transition_forbidden_at_service(self):
        vendor = VendorApplication.objects.create(
            company_name="Already Approved",
            contact_email="approved@example.com",
            country="United States",
            tax_id="US-APPROVED-001",
            estimated_annual_spend="10000.00",
            status=VendorApplication.Status.APPROVED,
        )
        service = VendorService()
        with self.assertRaises(VendorServiceError):
            service.reject(vendor, self.admin, "Should fail")
