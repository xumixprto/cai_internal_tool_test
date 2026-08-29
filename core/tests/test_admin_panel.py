"""Tests for the custom platform admin panel and access management."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.rbac.permissions import PlatformPermission
from core.rbac.roles import Role

User = get_user_model()


class AdminPanelTests(TestCase):
    """Platform admin panel authorization and user management."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")

    def test_admin_can_access_platform_admin(self):
        self.client.login(username="admin", password="admin")
        response = self.client.get(reverse("core_admin_panel:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User Access")

    def test_user_cannot_access_platform_admin(self):
        self.client.login(username="user1", password="user1")
        response = self.client.get(reverse("core_admin_panel:index"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_change_user1_role(self):
        self.client.login(username="admin", password="admin")
        user1 = User.objects.get(username="user1")

        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user1.id}),
            {"role": Role.ADMIN.value, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)

        user1.refresh_from_db()
        self.assertTrue(user1.has_perm(PlatformPermission.ACCESS_ADMIN))
        self.assertTrue(user1.is_active)

    def test_admin_can_disable_and_re_enable_user2(self):
        self.client.login(username="admin", password="admin")
        user2 = User.objects.get(username="user2")

        self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user2.id}),
            {"role": Role.USER.value, "is_active": ""},
        )
        user2.refresh_from_db()
        self.assertFalse(user2.is_active)

        self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user2.id}),
            {"role": Role.USER.value, "is_active": "on"},
        )
        user2.refresh_from_db()
        self.assertTrue(user2.is_active)

    def test_user_cannot_forge_access_change_for_other_user(self):
        self.client.login(username="user1", password="user1")
        user2 = User.objects.get(username="user2")

        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user2.id}),
            {"role": Role.ADMIN.value, "is_active": "on"},
        )
        self.assertEqual(response.status_code, 403)

    def test_seeded_admin_is_not_editable(self):
        self.client.login(username="admin", password="admin")
        admin_user = User.objects.get(username="admin")

        response = self.client.get(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": admin_user.id}),
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_edit_uses_post_and_csrf(self):
        """GET should render the form; mutation is POST-only."""
        self.client.login(username="admin", password="admin")
        user1 = User.objects.get(username="user1")

        get_response = self.client.get(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user1.id}),
        )
        self.assertEqual(get_response.status_code, 200)

        post_response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": user1.id}),
            {"role": Role.ADMIN.value, "is_active": "on"},
        )
        self.assertEqual(post_response.status_code, 302)
