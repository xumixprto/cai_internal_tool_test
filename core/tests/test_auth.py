"""Tests for authentication, login/logout, and protected routes."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.navigation.registry import get_nav_items

User = get_user_model()


class AuthenticationTests(TestCase):
    """Authentication and session behavior."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")

    def test_login_page_renders(self):
        response = self.client.get(reverse("core_authentication:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("core_authentication:login"),
            {"username": "admin", "password": "admin"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_invalid_login_rejected(self):
        response = self.client.post(
            reverse("core_authentication:login"),
            {"username": "admin", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username or password")

    def test_logout_terminates_session(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get(reverse("core_authentication:logout"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core_authentication:login"), response.url)

    def test_dashboard_shows_authenticated_user_and_role(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin")
        self.assertContains(response, "Admin")

    def test_login_for_disabled_user_rejected(self):
        user = User.objects.get(username="user2")
        user.is_active = False
        user.save()

        response = self.client.post(
            reverse("core_authentication:login"),
            {"username": "user2", "password": "user2"},
        )
        self.assertEqual(response.status_code, 200)

    def test_admin_navigation_visible_for_admin(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Admin")

    def test_admin_navigation_hidden_for_user(self):
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "Admin")

    def test_nav_items_filter_by_role(self):
        call_command("seed_demo_users")
        admin = User.objects.get(username="admin")
        user1 = User.objects.get(username="user1")

        request_admin = RequestFactory().get(reverse("dashboard"))
        request_admin.user = admin
        request_user = RequestFactory().get(reverse("dashboard"))
        request_user.user = user1

        admin_items = [item["key"] for item in get_nav_items(request_admin)]
        user_items = [item["key"] for item in get_nav_items(request_user)]

        self.assertIn("admin", admin_items)
        self.assertNotIn("admin", user_items)
