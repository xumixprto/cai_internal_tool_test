"""Tests for action-permission management in the Platform Admin UI."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from core.app_registry import AppAction, AppManifest, registry
from core.app_registry.services import set_user_app_access, sync_app_permissions
from core.rbac.roles import Role
from core.rbac.services import can, can_perform_action

User = get_user_model()


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


@override_settings(ROOT_URLCONF="core.tests.urls")
class AdminActionPermissionTests(TestCase):
    """Admin UI renders and persists app action permissions."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.admin_user = User.objects.create_user(username="action_admin", password="pw")
        self.admin_user.groups.set([admin_group])
        self.target_user = User.objects.create_user(username="action_target", password="pw")
        self.target_user.groups.set([user_group])

        # Create an unrelated permission to verify it is preserved.
        self.extra_permission = Permission.objects.create(
            codename="extra_perm",
            name="Extra Permission",
            content_type_id=Permission.objects.first().content_type_id,
        )
        self.target_user.user_permissions.add(self.extra_permission)

        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:test_one_index",
            access_permission="test_app.access",
            actions=[
                AppAction(
                    key="approve",
                    permission="test_app.approve",
                    label="Approve",
                ),
                AppAction(
                    key="reject",
                    permission="test_app.reject",
                    label="Reject",
                ),
            ],
        )
        registry.register(manifest)
        sync_app_permissions()
        _refresh_user(self.admin_user)
        _refresh_user(self.target_user)

    def tearDown(self):
        registry.reset()

    def test_edit_page_renders_action_checkboxes(self):
        self.client.login(username="action_admin", password="pw")
        response = self.client.get(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.target_user.id}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test App")
        self.assertContains(response, "Approve")
        self.assertContains(response, "Reject")
        self.assertContains(response, "app_action_test_app_approve")
        self.assertContains(response, "app_action_test_app_reject")

    def test_admin_can_grant_and_revoke_action_permissions(self):
        self.client.login(username="action_admin", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.target_user.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app": "on",
                "app_action_test_app_approve": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        _refresh_user(self.target_user)
        self.assertTrue(can(self.target_user, "test_app.access"))
        self.assertTrue(can(self.target_user, "test_app.approve"))
        self.assertFalse(can(self.target_user, "test_app.reject"))
        self.assertTrue(can_perform_action(self.target_user, "test_app", "approve"))

    def test_revoking_access_preserves_action_permissions(self):
        set_user_app_access(
            self.target_user,
            {"test_app"},
            {"test_app.approve", "test_app.reject"},
        )
        _refresh_user(self.target_user)
        self.assertTrue(can(self.target_user, "test_app.approve"))

        self.client.login(username="action_admin", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.target_user.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        _refresh_user(self.target_user)
        # App access is removed.
        self.assertFalse(can(self.target_user, "test_app.access"))
        # Action permissions are kept, but ineffective without app access.
        self.assertTrue(can(self.target_user, "test_app.approve"))
        self.assertFalse(can_perform_action(self.target_user, "test_app", "approve"))

    def test_unrelated_permissions_are_preserved(self):
        self.client.login(username="action_admin", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.target_user.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app": "on",
                "app_action_test_app_approve": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        _refresh_user(self.target_user)
        self.assertTrue(
            self.target_user.user_permissions.filter(pk=self.extra_permission.id).exists()
        )

    def test_non_admin_cannot_modify_permissions(self):
        non_admin = User.objects.create_user(username="non_admin_target", password="pw")
        non_admin.groups.set([Group.objects.get(name=Role.USER.value)])
        self.client.login(username="non_admin_target", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.target_user.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app": "on",
            },
        )
        self.assertEqual(response.status_code, 403)
