"""Tests for the App Registry, app permissions, navigation, and dashboard."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from core.app_registry import AppManifest, registry
from core.app_registry.services import (
    app_access_permissions,
    apps_for_user,
    set_user_app_access,
    sync_app_permissions,
)
from core.rbac.roles import Role
from core.rbac.services import can, can_access_app

User = get_user_model()


def _refresh_user(user):
    user.refresh_from_db()
    for attr in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
        user.__dict__.pop(attr, None)
    return user


class RegistryTests(TestCase):
    """In-memory App Registry behavior."""

    def tearDown(self):
        registry.reset()

    def test_register_and_retrieve_manifest(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:test_app_index",
            access_permission="test_app.access",
        )
        registry.register(manifest)
        self.assertTrue(registry.contains("test_app"))
        self.assertEqual(registry.get("test_app"), manifest)

    def test_register_is_idempotent_for_identical_manifest(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:test_app_index",
            access_permission="test_app.access",
        )
        registry.register(manifest)
        registry.register(manifest)
        self.assertEqual(len(registry.all()), 1)

    def test_register_different_manifest_same_key_raises(self):
        manifest_a = AppManifest(
            key="test_app",
            name="Test App A",
            description="A test app.",
            url_name="test_apps:a",
            access_permission="test_app.access",
        )
        manifest_b = AppManifest(
            key="test_app",
            name="Test App B",
            description="Another test app.",
            url_name="test_apps:b",
            access_permission="test_app.access",
        )
        registry.register(manifest_a)
        with self.assertRaises(ValueError):
            registry.register(manifest_b)

    def test_invalid_key_raises(self):
        with self.assertRaises(ValueError):
            AppManifest(
                key="1bad",
                name="Bad",
                description="Bad.",
                url_name="test_apps:index",
                access_permission="bad.access",
            )

    def test_invalid_access_permission_raises(self):
        with self.assertRaises(ValueError):
            AppManifest(
                key="bad",
                name="Bad",
                description="Bad.",
                url_name="test_apps:index",
                access_permission="no-dot",
            )

    def test_registry_ordering(self):
        first = AppManifest(
            key="alpha",
            name="Alpha",
            description="First.",
            url_name="test_apps:alpha",
            access_permission="alpha.access",
            order=10,
        )
        second = AppManifest(
            key="beta",
            name="Beta",
            description="Second.",
            url_name="test_apps:beta",
            access_permission="beta.access",
            order=20,
        )
        third = AppManifest(
            key="gamma",
            name="Gamma",
            description="Third.",
            url_name="test_apps:gamma",
            access_permission="gamma.access",
            order=10,
        )
        registry.register(second)
        registry.register(first)
        registry.register(third)
        keys = [app.key for app in registry.all()]
        self.assertEqual(keys, ["alpha", "gamma", "beta"])


class PermissionSyncTests(TestCase):
    """Application permission synchronization."""

    def tearDown(self):
        registry.reset()

    def test_sync_creates_access_and_action_permissions(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:index",
            access_permission="test_app.access",
            actions={"approve": "test_app.approve", "reject": "test_app.reject"},
        )
        registry.register(manifest)
        sync_app_permissions()

        admin_user = User.objects.create_superuser(username="sync_admin", password="pw")
        _refresh_user(admin_user)
        self.assertTrue(admin_user.has_perm("test_app.access"))
        self.assertTrue(admin_user.has_perm("test_app.approve"))
        self.assertTrue(admin_user.has_perm("test_app.reject"))

    def test_sync_is_idempotent(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:index",
            access_permission="test_app.access",
        )
        registry.register(manifest)
        sync_app_permissions()
        from django.contrib.auth.models import Permission

        permission_count = Permission.objects.filter(
            content_type__app_label="test_app",
        ).count()
        sync_app_permissions()
        second_count = Permission.objects.filter(
            content_type__app_label="test_app",
        ).count()
        self.assertEqual(second_count, permission_count)


@override_settings(ROOT_URLCONF="core.tests.urls")
class NavigationAndDashboardTests(TestCase):
    """Registry-driven navigation and dashboard."""

    def _register_test_apps(self):
        self.manifest_one = AppManifest(
            key="test_app_one",
            name="Test App One",
            description="First test app.",
            url_name="test_apps:test_one_index",
            access_permission="test_app_one.access",
            order=50,
        )
        self.manifest_two = AppManifest(
            key="test_app_two",
            name="Test App Two",
            description="Second test app.",
            url_name="test_apps:test_two_index",
            access_permission="test_app_two.access",
            order=60,
        )
        registry.register(self.manifest_one)
        registry.register(self.manifest_two)

    def _create_users(self):
        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.admin_user = User.objects.create_user(username="nav_admin", password="pw")
        self.admin_user.groups.set([admin_group])
        self.normal_user = User.objects.create_user(username="nav_user", password="pw")
        self.normal_user.groups.set([user_group])

    def tearDown(self):
        registry.reset()

    def test_empty_registry_yields_zero_apps(self):
        self._create_users()
        self.assertEqual(apps_for_user(self.admin_user), [])
        self.assertEqual(apps_for_user(self.normal_user), [])

    def test_apps_for_user_filters_by_access(self):
        self._create_users()
        self._register_test_apps()
        sync_app_permissions()
        set_user_app_access(self.normal_user, {"test_app_one"})
        _refresh_user(self.normal_user)

        visible = [app["key"] for app in apps_for_user(self.normal_user)]
        self.assertEqual(visible, ["test_app_one"])

    def test_admin_sees_all_apps(self):
        self._create_users()
        self._register_test_apps()
        sync_app_permissions()
        _refresh_user(self.admin_user)

        visible = [app["key"] for app in apps_for_user(self.admin_user)]
        self.assertEqual(visible, ["test_app_one", "test_app_two"])

    def test_dashboard_cards_match_registry(self):
        self._create_users()
        self._register_test_apps()
        sync_app_permissions()
        set_user_app_access(self.normal_user, {"test_app_one"})
        self.client.login(username="nav_user", password="pw")

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test App One")
        self.assertNotContains(response, "Test App Two")
        self.assertContains(response, "Applications")

    def test_navigation_shows_allowed_app_and_hides_denied(self):
        self._create_users()
        self._register_test_apps()
        sync_app_permissions()
        set_user_app_access(self.normal_user, {"test_app_one"})
        self.client.login(username="nav_user", password="pw")

        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Test App One")
        self.assertNotContains(response, "Test App Two")
        self.assertNotContains(response, "platform-admin")

    def test_admin_navigation_shows_business_apps(self):
        self._create_users()
        self._register_test_apps()
        sync_app_permissions()
        _refresh_user(self.admin_user)
        self.client.login(username="nav_admin", password="pw")

        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Test App One")
        self.assertContains(response, "Test App Two")
        self.assertContains(response, reverse("core_admin_panel:index"))

    def test_dashboard_empty_state(self):
        self._create_users()
        self.client.login(username="nav_user", password="pw")
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "0")
        self.assertContains(response, "No applications")


@override_settings(ROOT_URLCONF="core.tests.urls")
class RouteAuthorizationTests(TestCase):
    """Route-level application access enforcement."""

    def tearDown(self):
        registry.reset()
        if hasattr(self, "client"):
            self.client.logout()

    def _setup_apps_and_users(self):
        manifest_one = AppManifest(
            key="test_app_one",
            name="Test App One",
            description="First test app.",
            url_name="test_apps:test_one_index",
            access_permission="test_app_one.access",
        )
        manifest_two = AppManifest(
            key="test_app_two",
            name="Test App Two",
            description="Second test app.",
            url_name="test_apps:test_two_index",
            access_permission="test_app_two.access",
        )
        registry.register(manifest_one)
        registry.register(manifest_two)
        sync_app_permissions()

        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.granted_user = User.objects.create_user(username="granted", password="pw")
        self.granted_user.groups.set([user_group])
        self.denied_user = User.objects.create_user(username="denied", password="pw")
        self.denied_user.groups.set([user_group])
        self.admin_user = User.objects.create_user(username="app_admin", password="pw")
        self.admin_user.groups.set([admin_group])

        set_user_app_access(self.granted_user, {"test_app_one"})
        _refresh_user(self.granted_user)
        _refresh_user(self.denied_user)
        _refresh_user(self.admin_user)

    def test_authorized_user_gets_200(self):
        self._setup_apps_and_users()
        self.client.login(username="granted", password="pw")
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_gets_403(self):
        self._setup_apps_and_users()
        self.client.login(username="denied", password="pw")
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirects_to_login(self):
        self._setup_apps_and_users()
        response = self.client.get(reverse("test_apps:test_one_index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_admin_accesses_any_app(self):
        self._setup_apps_and_users()
        self.client.login(username="app_admin", password="pw")
        response = self.client.get(reverse("test_apps:test_two_index"))
        self.assertEqual(response.status_code, 200)


class AdminAppAccessTests(TestCase):
    """Per-user application access in the Platform Admin panel."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        self.admin_user = User.objects.create_user(username="admin_access_admin", password="pw")
        self.admin_user.groups.set([admin_group])
        self.user1 = User.objects.create_user(username="admin_access_user1", password="pw")
        self.user1.groups.set([user_group])

        manifest_one = AppManifest(
            key="test_app_one",
            name="Test App One",
            description="First test app.",
            url_name="test_apps:test_one_index",
            access_permission="test_app_one.access",
        )
        manifest_two = AppManifest(
            key="test_app_two",
            name="Test App Two",
            description="Second test app.",
            url_name="test_apps:test_two_index",
            access_permission="test_app_two.access",
        )
        registry.register(manifest_one)
        registry.register(manifest_two)
        sync_app_permissions()
        # Force fresh permission caches for the form's initial state.
        _refresh_user(self.admin_user)
        _refresh_user(self.user1)

    def tearDown(self):
        registry.reset()

    def test_edit_page_renders_dynamic_app_checkboxes(self):
        self.client.login(username="admin_access_admin", password="pw")
        response = self.client.get(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.user1.id}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Access")
        self.assertContains(response, "Test App One")
        self.assertContains(response, "Test App Two")
        self.assertContains(response, "app_access_test_app_one")

    def test_saving_checkbox_grants_access(self):
        self.client.login(username="admin_access_admin", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.user1.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app_one": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        _refresh_user(self.user1)
        self.assertTrue(can_access_app(self.user1, "test_app_one"))
        self.assertFalse(can_access_app(self.user1, "test_app_two"))

    def test_saving_checkbox_removes_access(self):
        set_user_app_access(self.user1, {"test_app_one"})
        _refresh_user(self.user1)
        self.assertTrue(can_access_app(self.user1, "test_app_one"))

        self.client.login(username="admin_access_admin", password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.user1.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app_one": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        _refresh_user(self.user1)
        self.assertFalse(can_access_app(self.user1, "test_app_one"))

    def test_user_cannot_self_grant_access(self):
        self.user1.is_staff = False
        self.user1.save()
        self.client.login(username=self.user1.username, password="pw")
        response = self.client.post(
            reverse("core_admin_panel:user_edit", kwargs={"user_id": self.user1.id}),
            {
                "role": Role.USER.value,
                "is_active": "on",
                "app_access_test_app_one": "on",
            },
        )
        self.assertEqual(response.status_code, 403)


class AdminPermissionTests(TestCase):
    """Admin group receives all registered application permissions."""

    def tearDown(self):
        registry.reset()

    def test_admin_has_all_app_permissions(self):
        from django.contrib.auth.models import Group

        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:index",
            access_permission="test_app.access",
            actions={"approve": "test_app.approve"},
        )
        registry.register(manifest)
        sync_app_permissions()

        admin_group = Group.objects.get(name=Role.ADMIN.value)
        admin_user = User.objects.create_user(username="perm_admin", password="pw")
        admin_user.groups.set([admin_group])
        _refresh_user(admin_user)
        self.assertTrue(admin_user.has_perm("test_app.access"))
        self.assertTrue(admin_user.has_perm("test_app.approve"))

    def test_can_helper_works(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:index",
            access_permission="test_app.access",
            actions={"approve": "test_app.approve"},
        )
        registry.register(manifest)
        sync_app_permissions()

        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        user = User.objects.create_user(username="can_user", password="pw")
        user.groups.set([user_group])
        set_user_app_access(user, {"test_app"})
        _refresh_user(user)

        self.assertTrue(can(user, "test_app.access"))
        self.assertFalse(can(user, "test_app.approve"))


class AppAccessPermissionStateTests(TestCase):
    """User-level application access permission status."""

    def tearDown(self):
        registry.reset()

    def test_app_access_permissions_reflect_user_grants(self):
        manifest = AppManifest(
            key="test_app",
            name="Test App",
            description="A test app.",
            url_name="test_apps:index",
            access_permission="test_app.access",
        )
        registry.register(manifest)
        sync_app_permissions()

        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)
        admin_user = User.objects.create_user(username="state_admin", password="pw")
        admin_user.groups.set([admin_group])
        user = User.objects.create_user(username="state_user", password="pw")
        user.groups.set([user_group])
        set_user_app_access(user, {"test_app"})

        states = {
            entry["app"].key: entry["granted"] for entry in app_access_permissions(admin_user)
        }
        self.assertTrue(states["test_app"])

        states = {entry["app"].key: entry["granted"] for entry in app_access_permissions(user)}
        self.assertTrue(states["test_app"])
