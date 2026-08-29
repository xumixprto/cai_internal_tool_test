"""Regression tests for the platform navigation sidebar."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.kyc.models.kyc import KYCApplication
from apps.refunds.models.refund import RefundRequest
from apps.vendors.models.vendor import VendorApplication
from core.app_registry import registry
from core.app_registry.services import set_user_app_access

User = get_user_model()


class SidebarNavigationRegressionTests(TestCase):
    """Ensure authorized business apps remain visible in the sidebar on every page."""

    @classmethod
    def setUpTestData(cls):
        # Re-register real business apps in case an earlier test reset the
        # global in-memory registry.  The seed command relies on the registry
        # being populated to create app permissions.
        from apps.kyc.manifest import manifest as kyc_manifest
        from apps.refunds.manifest import manifest as refunds_manifest
        from apps.vendors.manifest import manifest as vendors_manifest

        for manifest in (refunds_manifest, vendors_manifest, kyc_manifest):
            registry.register(manifest)

        call_command("seed_demo_users")
        call_command("seed_refund_demo_data")
        call_command("seed_vendor_demo_data")
        call_command("seed_kyc_demo_data")

        cls.user = User.objects.create_user(username="multi_app_user", password="pw")
        set_user_app_access(
            cls.user,
            {"refunds", "vendors", "kyc"},
            {
                "refunds.approve",
                "refunds.reject",
                "vendors.approve",
                "vendors.request_changes",
                "kyc.approve",
                "kyc.reject",
                "kyc.escalate",
            },
        )

    def _nav_keys(self, response):
        """Return the sidebar nav item keys from a rendered response."""
        if response.context is None:
            self.fail("Response has no context; page did not render with the shell.")
        if isinstance(response.context, list):
            context = response.context[0] if response.context else {}
        else:
            context = response.context
        nav_items = context.get("nav_items")
        if nav_items is None:
            self.fail("nav_items missing from response context")
        return [item["key"] for item in nav_items]

    def test_dashboard_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_refund_queue_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        response = self.client.get(reverse("refunds:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_refund_detail_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        refund = RefundRequest.objects.first()
        response = self.client.get(reverse("refunds:detail", args=[refund.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_vendor_queue_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        response = self.client.get(reverse("vendors:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_vendor_detail_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        vendor = VendorApplication.objects.first()
        response = self.client.get(reverse("vendors:detail", args=[vendor.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_kyc_queue_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        response = self.client.get(reverse("kyc:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_kyc_detail_shows_all_authorized_apps(self):
        self.client.login(username="multi_app_user", password="pw")
        case = KYCApplication.objects.first()
        response = self.client.get(reverse("kyc:detail", args=[case.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_post_redirect_preserves_navigation(self):
        self.client.login(username="multi_app_user", password="pw")
        case = KYCApplication.objects.create(
            customer_name="Reject Me",
            customer_identifier="KYC-NAV-001",
            country="United States",
            date_of_birth="1985-06-12",
            document_type=KYCApplication.DocumentType.PASSPORT,
            document_identifier="US-NAV-001",
            risk_score=20,
            risk_level=KYCApplication.RiskLevel.LOW,
            status=KYCApplication.Status.UNDER_REVIEW,
            provider_verification_status=KYCApplication.ProviderVerificationStatus.VERIFIED,
        )
        response = self.client.post(
            reverse("kyc:reject", args=[case.pk]),
            {"reason": "Navigation test rejection"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._nav_keys(response),
            ["dashboard", "refunds", "vendors", "kyc"],
        )

    def test_unauthorized_app_is_hidden(self):
        limited = User.objects.create_user(username="limited", password="pw")
        set_user_app_access(limited, {"refunds"})
        self.client.login(username="limited", password="pw")

        response = self.client.get(reverse("refunds:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._nav_keys(response), ["dashboard", "refunds"])

        # Direct access to unauthorized app is denied, and the unauthorized
        # app does not leak into the sidebar on the 403 page.
        response = self.client.get(reverse("kyc:index"))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("kyc", self._nav_keys(response))

    def test_admin_sees_all_apps(self):
        self.client.logout()
        self.client.login(username="admin", password="admin")
        for url_name in ("dashboard", "refunds:index", "vendors:index", "kyc:index"):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)
            keys = self._nav_keys(response)
            self.assertIn("refunds", keys)
            self.assertIn("vendors", keys)
            self.assertIn("kyc", keys)
            self.assertIn("admin", keys)

    def test_sequential_navigation_between_apps(self):
        """Clicking through app pages must never drop an authorized app from the sidebar."""
        self.client.login(username="multi_app_user", password="pw")
        urls = [
            reverse("dashboard"),
            reverse("refunds:index"),
            reverse("vendors:index"),
            reverse("kyc:index"),
            reverse("refunds:index"),
            reverse("dashboard"),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                self._nav_keys(response),
                ["dashboard", "refunds", "vendors", "kyc"],
            )
