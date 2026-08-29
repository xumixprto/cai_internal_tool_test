"""Tests for the developer component showcase page."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from core.app_registry.services import sync_app_permissions
from core.rbac.roles import Role

User = get_user_model()


@override_settings(DEBUG=True)
class DevComponentsTests(TestCase):
    """Access rules for the developer-only component showcase."""

    def _create_users(self):
        sync_app_permissions()
        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.admin_user = User.objects.create_user(username="dev_admin", password="pw")
        self.admin_user.groups.set([admin_group])
        self.normal_user = User.objects.create_user(username="dev_user", password="pw")
        self.normal_user.groups.set([user_group])

    def test_admin_can_access_showcase(self):
        self._create_users()
        self.client.login(username="dev_admin", password="pw")
        response = self.client.get(reverse("dev_components"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Component Showcase")

    def test_normal_user_forbidden(self):
        self._create_users()
        self.client.login(username="dev_user", password="pw")
        response = self.client.get(reverse("dev_components"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse("dev_components"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    @override_settings(DEBUG=False)
    def test_showcase_returns_404_when_debug_false(self):
        self._create_users()
        self.client.login(username="dev_admin", password="pw")
        response = self.client.get(reverse("dev_components"))
        self.assertEqual(response.status_code, 404)
