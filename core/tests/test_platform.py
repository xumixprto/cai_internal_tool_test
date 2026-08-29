from django.test import TestCase
from django.urls import resolve, reverse


class PlatformIntegrationTests(TestCase):
    """Smoke tests for the platform shell and navigation."""

    def test_dashboard_returns_200(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internal Tools")

    def test_demo_one_returns_200(self):
        response = self.client.get(reverse("demo_one:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demo App One")

    def test_demo_two_returns_200(self):
        response = self.client.get(reverse("demo_two:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demo App Two")

    def test_navigation_present_on_dashboard(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Demo App One")
        self.assertContains(response, "Demo App Two")

    def test_shared_shell_present(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Internal Tools Platform")
        self.assertContains(response, "sidebar")

    def test_no_login_required(self):
        """All public pages should be reachable without authentication."""
        for url_name in ("dashboard", "demo_one:index", "demo_two:index"):
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_url_namespaces_resolve(self):
        self.assertEqual(reverse("dashboard"), "/")
        self.assertEqual(reverse("demo_one:index"), "/apps/demo-one/")
        self.assertEqual(reverse("demo_two:index"), "/apps/demo-two/")
        self.assertEqual(resolve("/").view_name, "dashboard")
        self.assertEqual(resolve("/apps/demo-one/").view_name, "demo_one:index")
        self.assertEqual(resolve("/apps/demo-two/").view_name, "demo_two:index")
