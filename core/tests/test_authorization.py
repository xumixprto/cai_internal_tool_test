"""Tests for app and action authorization helpers."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from core.app_registry import AppAction, AppManifest, registry
from core.app_registry.services import set_user_app_access, sync_app_permissions
from core.rbac.roles import Role
from core.rbac.services import can_perform_action

User = get_user_model()


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


@override_settings(ROOT_URLCONF="core.tests.urls")
class AppAuthorizationTests(TestCase):
    """Function and class-based app/action authorization."""

    def tearDown(self):
        registry.reset()

    def _setup_manifest(self):
        manifest = AppManifest(
            key="test_app_one",
            name="Test App One",
            description="First test app.",
            url_name="test_apps:test_one_index",
            access_permission="test_app_one.access",
            actions=[
                AppAction(
                    key="approve",
                    permission="test_app_one.approve",
                    label="Approve",
                ),
                AppAction(
                    key="reject",
                    permission="test_app_one.reject",
                    label="Reject",
                ),
            ],
        )
        registry.register(manifest)
        sync_app_permissions()

    def _create_users(self):
        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.admin_user = User.objects.create_user(username="auth_admin", password="pw")
        self.admin_user.groups.set([admin_group])
        self.authorized_user = User.objects.create_user(username="auth_user", password="pw")
        self.authorized_user.groups.set([user_group])
        self.denied_user = User.objects.create_user(username="denied_user", password="pw")
        self.denied_user.groups.set([user_group])

        set_user_app_access(self.authorized_user, {"test_app_one"})
        _refresh_user(self.authorized_user)
        _refresh_user(self.denied_user)
        _refresh_user(self.admin_user)

    def test_require_app_access_redirects_anonymous(self):
        self._setup_manifest()
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_require_app_access_allows_authorized_user(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test app one")

    def test_require_app_access_denies_unauthorized_user(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="denied_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 403)

    def test_app_access_required_mixin_allows_authorized_user(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_cbv"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cbv list")

    def test_app_access_required_mixin_denies_unauthorized_user(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="denied_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_cbv"))
        self.assertEqual(response.status_code, 403)

    def test_can_perform_action_requires_access_and_action(self):
        self._setup_manifest()
        self._create_users()
        self.assertFalse(can_perform_action(self.authorized_user, "test_app_one", "approve"))

        set_user_app_access(
            self.authorized_user,
            {"test_app_one"},
            {"test_app_one.approve"},
        )
        _refresh_user(self.authorized_user)
        self.assertTrue(can_perform_action(self.authorized_user, "test_app_one", "approve"))
        self.assertFalse(can_perform_action(self.authorized_user, "test_app_one", "reject"))

    def test_action_without_app_access_is_denied(self):
        self._setup_manifest()
        self._create_users()
        # Grant only the action permission, not app access.
        set_user_app_access(
            self.denied_user,
            set(),
            {"test_app_one.approve"},
        )
        _refresh_user(self.denied_user)
        self.assertFalse(can_perform_action(self.denied_user, "test_app_one", "approve"))

    def test_require_app_action_redirects_anonymous(self):
        self._setup_manifest()
        response = self.client.get(reverse("test_apps:test_one_approve"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_require_app_action_allows_with_both_permissions(self):
        self._setup_manifest()
        self._create_users()
        set_user_app_access(
            self.authorized_user,
            {"test_app_one"},
            {"test_app_one.approve"},
        )
        _refresh_user(self.authorized_user)
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_approve"))
        self.assertEqual(response.status_code, 200)

    def test_require_app_action_denies_without_action_permission(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_approve"))
        self.assertEqual(response.status_code, 403)

    def test_app_action_required_mixin_allows_with_both_permissions(self):
        self._setup_manifest()
        self._create_users()
        set_user_app_access(
            self.authorized_user,
            {"test_app_one"},
            {"test_app_one.reject"},
        )
        _refresh_user(self.authorized_user)
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_reject"))
        self.assertEqual(response.status_code, 200)

    def test_app_action_required_mixin_denies_without_action(self):
        self._setup_manifest()
        self._create_users()
        self.client.login(username="auth_user", password="pw")
        response = self.client.get(reverse("test_apps:test_one_reject"))
        self.assertEqual(response.status_code, 403)
