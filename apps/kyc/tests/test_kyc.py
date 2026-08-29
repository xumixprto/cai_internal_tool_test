"""Tests for the KYC Review app."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.kyc.models.kyc import KYCApplication
from apps.kyc.providers.kyc_provider import KYCProvider
from apps.kyc.services.kyc import KYCService, KYCServiceError
from core.app_registry.services import set_user_app_access, sync_app_permissions

User = get_user_model()


class FixedIdentityProvider(KYCProvider):
    """Test provider that returns deterministic verification results."""

    def __init__(self, outcome="verified"):
        self.outcome = outcome

    def verify_identity(self, case):
        if self.outcome == "verified":
            return {
                "identity_match": True,
                "document_verified": True,
                "screening_result": "clear",
                "screening_flags": "Sanctions clear; PEP clear",
                "provider_reference": "KYC-TEST-123",
            }
        if self.outcome == "flagged":
            return {
                "identity_match": True,
                "document_verified": True,
                "screening_result": "flagged",
                "screening_flags": "PEP match",
                "provider_reference": "KYC-TEST-FLAG",
            }
        return {
            "identity_match": True,
            "document_verified": False,
            "screening_result": "failed",
            "screening_flags": "Document could not be verified",
            "provider_reference": "KYC-TEST-FAIL",
        }


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


class KYCServiceTests(TestCase):
    """KYC business rules and service behavior."""

    def setUp(self):
        self.actor = User.objects.create_user(username="service_actor", password="pw")
        self.target_user = User.objects.create_user(username="assigned_user", password="pw")
        self.case = KYCApplication.objects.create(
            customer_name="Test Customer",
            customer_identifier="KYC-TEST-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-TEST-001",
            risk_score=50,
            risk_level=KYCApplication.RiskLevel.MEDIUM,
            status=KYCApplication.Status.PENDING,
        )
        sync_app_permissions()

    def _to_under_review(self):
        KYCService().move_to_under_review(self.case, self.actor)
        self.case.refresh_from_db()

    def test_move_to_under_review(self):
        KYCService().move_to_under_review(self.case, self.actor)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, KYCApplication.Status.UNDER_REVIEW)

    def test_approve_requires_under_review(self):
        with self.assertRaises(KYCServiceError):
            KYCService(provider=FixedIdentityProvider()).approve(self.case, self.actor)

    def test_approve_sets_status_and_reference(self):
        self._to_under_review()
        KYCService(provider=FixedIdentityProvider()).approve(self.case, self.actor)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, KYCApplication.Status.APPROVED)
        self.assertEqual(self.case.provider_reference, "KYC-TEST-123")

    def test_approved_case_cannot_be_approved_again(self):
        self._to_under_review()
        service = KYCService(provider=FixedIdentityProvider())
        service.approve(self.case, self.actor)
        with self.assertRaises(KYCServiceError):
            service.approve(self.case, self.actor)

    def test_approve_rejects_flagged_provider_result(self):
        self._to_under_review()
        with self.assertRaises(KYCServiceError):
            KYCService(provider=FixedIdentityProvider("flagged")).approve(self.case, self.actor)

    def test_approve_rejects_failed_provider_result(self):
        self._to_under_review()
        with self.assertRaises(KYCServiceError):
            KYCService(provider=FixedIdentityProvider("failed")).approve(self.case, self.actor)

    def test_reject_requires_reason(self):
        with self.assertRaises(KYCServiceError):
            KYCService().reject(self.case, self.actor, "   ")

    def test_reject_sets_status_and_reason(self):
        KYCService().reject(self.case, self.actor, "Suspicious identity")
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, KYCApplication.Status.REJECTED)
        self.assertEqual(self.case.rejection_reason, "Suspicious identity")

        from shared.services.primitives import status_history

        record = status_history.latest_for(self.case)
        self.assertEqual(record.note, "Suspicious identity")

    def test_rejected_case_cannot_be_approved(self):
        KYCService().reject(self.case, self.actor, "Suspicious identity")
        self.case.refresh_from_db()
        with self.assertRaises(KYCServiceError):
            KYCService(provider=FixedIdentityProvider()).approve(self.case, self.actor)

    def test_escalate_requires_reason(self):
        self._to_under_review()
        with self.assertRaises(KYCServiceError):
            KYCService().escalate(self.case, self.actor, "   ")

    def test_escalate_and_return_to_under_review(self):
        self._to_under_review()
        KYCService().escalate(self.case, self.actor, "Potential sanctions match")
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, KYCApplication.Status.ESCALATED)

        KYCService().move_to_under_review(self.case, self.actor)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, KYCApplication.Status.UNDER_REVIEW)

    def test_escalate_not_allowed_after_approval(self):
        self._to_under_review()
        KYCService(provider=FixedIdentityProvider()).approve(self.case, self.actor)
        self.case.refresh_from_db()
        with self.assertRaises(KYCServiceError):
            KYCService().escalate(self.case, self.actor, "Should fail")

    def test_assign_creates_history(self):
        service = KYCService()
        record = service.assign(self.case, self.target_user, self.actor)
        current = service.get_current_assignment(self.case)
        self.assertEqual(current.assigned_to, self.target_user)
        self.assertEqual(record.assigned_to, self.target_user)

    def test_add_note_creates_comment_and_audit(self):
        service = KYCService()
        note = service.add_note(self.case, self.actor, "Important context")
        self.assertEqual(note.body, "Important context")
        self.assertEqual(service.get_notes(self.case).count(), 1)

    def test_activity_contains_status_and_notes(self):
        service = KYCService()
        service.assign(self.case, self.target_user, self.actor)
        service.add_note(self.case, self.actor, "note")
        service.move_to_under_review(self.case, self.actor)

        activity = service.get_activity(self.case)
        self.assertTrue(any(entry["type"] == "note" for entry in activity))
        self.assertTrue(any(entry["type"] == "status" for entry in activity))
        self.assertTrue(any(entry["type"] == "assignment" for entry in activity))
        self.assertTrue(any(entry["type"] == "submitted" for entry in activity))


class KYCViewsTests(TestCase):
    """KYC queue, detail, and action views."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")
        call_command("seed_kyc_demo_data")
        sync_app_permissions()

    def setUp(self):
        self.admin = User.objects.get(username="admin")
        self.user1 = User.objects.get(username="user1")
        self.user2 = User.objects.get(username="user2")

    def test_manifest_appears_in_registry(self):
        from core.app_registry import registry

        self.assertIn("kyc", (m.key for m in registry.all()))

    def test_admin_receives_all_kyc_permissions(self):
        admin = _refresh_user(self.admin)
        self.assertTrue(admin.has_perm("kyc.access"))
        self.assertTrue(admin.has_perm("kyc.approve"))
        self.assertTrue(admin.has_perm("kyc.reject"))
        self.assertTrue(admin.has_perm("kyc.escalate"))
        self.assertTrue(admin.has_perm("kyc.assign"))

    def test_user_without_access_cannot_view_queue(self):
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("kyc:index"))
        self.assertEqual(response.status_code, 403)

    def test_granted_user_can_view_queue(self):
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("kyc:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KYC Review")

    def test_queue_filters_by_status(self):
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("kyc:index"), {"status": "approved"})
        self.assertEqual(response.status_code, 200)

    def test_queue_filters_by_risk(self):
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("kyc:index"), {"risk": "high"})
        self.assertEqual(response.status_code, 200)

    def test_queue_search_works(self):
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("kyc:index"), {"q": "Alex"})
        self.assertEqual(response.status_code, 200)

    def test_admin_can_start_review(self):
        case = KYCApplication.objects.filter(status=KYCApplication.Status.PENDING).first()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("kyc:review", args=[case.pk]))
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertEqual(case.status, KYCApplication.Status.UNDER_REVIEW)

    def test_admin_can_escalate_and_return(self):
        case = KYCApplication.objects.create(
            customer_name="Escalate Me",
            customer_identifier="KYC-ESCALATE-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-ESC-001",
            risk_score=50,
            risk_level=KYCApplication.RiskLevel.MEDIUM,
            status=KYCApplication.Status.UNDER_REVIEW,
        )
        self.client.login(username="admin", password="admin")
        response = self.client.post(
            reverse("kyc:escalate", args=[case.pk]),
            {"reason": "Sanctions match requires additional review"},
        )
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertEqual(case.status, KYCApplication.Status.ESCALATED)

        response = self.client.post(reverse("kyc:review", args=[case.pk]))
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertEqual(case.status, KYCApplication.Status.UNDER_REVIEW)

    def test_admin_can_approve_and_history_created(self):
        case = KYCApplication.objects.create(
            customer_name="Approve Me",
            customer_identifier="KYC-APPROVE-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-APP-001",
            risk_score=50,
            risk_level=KYCApplication.RiskLevel.MEDIUM,
            status=KYCApplication.Status.UNDER_REVIEW,
        )
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("kyc:approve", args=[case.pk]))
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertEqual(case.status, KYCApplication.Status.APPROVED)

    def test_unauthorized_approval_is_denied(self):
        case = KYCApplication.objects.filter(status=KYCApplication.Status.UNDER_REVIEW).first()
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(reverse("kyc:approve", args=[case.pk]))
        self.assertEqual(response.status_code, 403)

    def test_reject_requires_reason(self):
        case = KYCApplication.objects.filter(status=KYCApplication.Status.UNDER_REVIEW).first()
        self.client.login(username="admin", password="admin")
        response = self.client.post(reverse("kyc:reject", args=[case.pk]))
        self.assertEqual(response.status_code, 302)

        case.refresh_from_db()
        self.assertNotEqual(case.status, KYCApplication.Status.REJECTED)

    def test_assign_permission_controls_assignment(self):
        case = KYCApplication.objects.first()
        set_user_app_access(self.user1, {"kyc"}, {"kyc.assign"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("kyc:assign", args=[case.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 302)

        from shared.services.primitives import assignments

        current = assignments.current_for(case)
        self.assertEqual(current.assigned_to, self.admin)

    def test_user_without_assign_permission_cannot_assign(self):
        case = KYCApplication.objects.first()
        set_user_app_access(self.user2, {"kyc"})
        _refresh_user(self.user2)
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("kyc:assign", args=[case.pk]),
            {"assigned_to": self.admin.pk},
        )
        self.assertEqual(response.status_code, 403)

    def test_add_note_with_access(self):
        case = KYCApplication.objects.first()
        set_user_app_access(self.user1, {"kyc"})
        _refresh_user(self.user1)
        self.client.login(username="user1", password="user1")
        response = self.client.post(
            reverse("kyc:note", args=[case.pk]),
            {"body": "Customer confirmed identity."},
        )
        self.assertEqual(response.status_code, 302)

        from shared.services.primitives import comments

        self.assertEqual(comments.for_object(case).count(), 1)

    def test_user_without_access_cannot_add_note(self):
        case = KYCApplication.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.post(
            reverse("kyc:note", args=[case.pk]),
            {"body": "Should not be saved."},
        )
        self.assertEqual(response.status_code, 403)

    def test_forbidden_direct_detail_access(self):
        case = KYCApplication.objects.first()
        self.client.login(username="user2", password="user2")
        response = self.client.get(reverse("kyc:detail", args=[case.pk]))
        self.assertEqual(response.status_code, 403)

    def test_independent_access_across_apps(self):
        set_user_app_access(self.user1, {"refunds", "kyc"})
        set_user_app_access(self.user2, {"vendors"})
        _refresh_user(self.user1)
        _refresh_user(self.user2)

        self.client.login(username="user1", password="user1")
        self.assertEqual(self.client.get(reverse("refunds:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("kyc:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vendors:index")).status_code, 403)

        self.client.login(username="user2", password="user2")
        self.assertEqual(self.client.get(reverse("vendors:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("kyc:index")).status_code, 403)

    def test_action_permissions_independent_per_app(self):
        set_user_app_access(
            self.user2,
            {"kyc"},
            {"kyc.reject", "kyc.escalate", "kyc.assign"},
        )
        _refresh_user(self.user2)
        self.client.login(username="user2", password="user2")

        case = KYCApplication.objects.create(
            customer_name="Action Test",
            customer_identifier="KYC-ACTION-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-ACT-001",
            risk_score=50,
            risk_level=KYCApplication.RiskLevel.MEDIUM,
            status=KYCApplication.Status.UNDER_REVIEW,
        )

        reject_response = self.client.post(
            reverse("kyc:reject", args=[case.pk]),
            {"reason": "Rejected by user2"},
        )
        self.assertEqual(reject_response.status_code, 302)

        case.status = KYCApplication.Status.UNDER_REVIEW
        case.save()
        approve_response = self.client.post(reverse("kyc:approve", args=[case.pk]))
        self.assertEqual(approve_response.status_code, 403)

    def test_invalid_transition_forbidden_at_service(self):
        case = KYCApplication.objects.create(
            customer_name="Already Approved",
            customer_identifier="KYC-APPROVED-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-APV-001",
            risk_score=50,
            risk_level=KYCApplication.RiskLevel.MEDIUM,
            status=KYCApplication.Status.APPROVED,
        )
        service = KYCService()
        with self.assertRaises(KYCServiceError):
            service.reject(case, self.admin, "Should fail")
