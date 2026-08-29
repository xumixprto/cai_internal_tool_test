"""Tests for the RBAC abstraction and role behavior."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from core.rbac.permissions import PlatformPermission
from core.rbac.roles import Role
from core.rbac.services import get_user_role, has_permission, is_admin, set_user_access

User = get_user_model()


class RbacTests(TestCase):
    """Role-based access control behavior."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo_users")

    def test_seed_assigns_roles(self):
        admin = User.objects.get(username="admin")
        user1 = User.objects.get(username="user1")
        user2 = User.objects.get(username="user2")

        self.assertEqual(get_user_role(admin), Role.ADMIN)
        self.assertEqual(get_user_role(user1), Role.USER)
        self.assertEqual(get_user_role(user2), Role.USER)

    def test_is_admin_returns_correctly(self):
        admin = User.objects.get(username="admin")
        user1 = User.objects.get(username="user1")

        self.assertTrue(is_admin(admin))
        self.assertFalse(is_admin(user1))

    def test_has_permission_for_admin_access(self):
        admin = User.objects.get(username="admin")
        user1 = User.objects.get(username="user1")

        self.assertTrue(has_permission(admin, PlatformPermission.ACCESS_ADMIN))
        self.assertFalse(has_permission(user1, PlatformPermission.ACCESS_ADMIN))

    def test_set_user_access_updates_role(self):
        user1 = User.objects.get(username="user1")
        set_user_access(user1, Role.ADMIN, True)

        self.assertEqual(get_user_role(user1), Role.ADMIN)
        self.assertTrue(user1.has_perm(PlatformPermission.ACCESS_ADMIN))

    def test_set_user_access_disables_user(self):
        user1 = User.objects.get(username="user1")
        set_user_access(user1, Role.USER, False)

        self.assertFalse(user1.is_active)

    def test_role_change_takes_effect_immediately(self):
        user1 = User.objects.get(username="user1")

        set_user_access(user1, Role.ADMIN, True)
        self.assertTrue(is_admin(user1))

        set_user_access(user1, Role.USER, True)
        self.assertFalse(is_admin(user1))
