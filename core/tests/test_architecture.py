"""Architecture tests protecting the Internal Tools Platform boundaries."""

import ast
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from core.app_registry import AppAction, AppManifest, registry
from core.app_registry.services import apps_for_user
from core.navigation import CORE_NAV_ITEMS, get_nav_items


class PlatformArchitectureTests(TestCase):
    """Lightweight checks that the platform remains app-agnostic."""

    @classmethod
    def setUpTestData(cls):
        cls._restore_registry()

    @classmethod
    def _restore_registry(cls):
        registry.reset()
        # Re-register the real business apps just like AppConfig.ready() does.
        from apps.kyc.manifest import manifest as kyc_manifest
        from apps.refunds.manifest import manifest as refunds_manifest
        from apps.vendors.manifest import manifest as vendors_manifest

        for manifest in (refunds_manifest, vendors_manifest, kyc_manifest):
            registry.register(manifest)

    def test_core_does_not_import_apps(self):
        """core/ must not depend on application-specific code in apps/."""
        core_dir = Path(settings.BASE_DIR) / "core"
        violations = []

        for path in sorted(core_dir.rglob("*.py")):
            if "tests" in path.parts:
                continue
            if path.name == "test_architecture.py":
                continue
            source = path.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                violations.append(f"{path}: syntax error {exc}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "apps" or alias.name.startswith("apps."):
                            violations.append(f"{path}: import {alias.name}")
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "apps" or module.startswith("apps."):
                        violations.append(f"{path}: from {module} import")

        self.assertEqual(violations, [])

    def test_business_navigation_derives_from_registry(self):
        """Nav items for a user come from the App Registry + core nav entries."""
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory

        User = get_user_model()
        admin = User.objects.create_superuser(
            username="arch_nav_user",
            email="a@a.a",
            password="pw",
        )
        request = RequestFactory().get("/")
        request.user = admin

        nav_items = get_nav_items(request)
        nav_keys = [item["key"] for item in nav_items]

        core_keys = [item["key"] for item in CORE_NAV_ITEMS]
        for key in core_keys:
            self.assertIn(key, nav_keys)

        for app in registry.all():
            self.assertIn(app.key, nav_keys, f"{app.key} missing from nav")

    def test_app_visibility_uses_rbac(self):
        """apps_for_user only exposes apps the user is allowed to access."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="arch_rbac_user", password="pw")
        self.assertEqual(apps_for_user(user), [])

    def test_registered_app_urls_use_apps_prefix(self):
        """All registered business apps use the /apps/<key>/ URL convention."""
        failures = []
        for app in registry.all():
            try:
                resolved_url = reverse(app.url_name)
            except NoReverseMatch as exc:
                # Test-only manifests may not be mounted in every URLconf.
                if app.key in ("refunds", "vendors", "kyc"):
                    failures.append(f"{app.key}: {exc}")
                continue

            expected_prefix = f"/apps/{app.key}/"
            if not resolved_url.startswith(expected_prefix):
                failures.append(f"{app.key}: {resolved_url} does not start with {expected_prefix}")

        self.assertEqual(failures, [])

    def test_manifest_keys_are_unique(self):
        """The registry cannot contain duplicate app keys."""
        keys = [app.key for app in registry.all()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_manifest_validation_rejects_inconsistent_access_permission(self):
        """Fail-fast when the access permission does not follow the <key>.access convention."""
        with self.assertRaises(ValueError) as ctx:
            AppManifest(
                key="sample",
                name="Sample",
                description="Test.",
                url_name="sample:index",
                access_permission="other.access",
            )
        self.assertIn("access_permission", str(ctx.exception))

    def test_manifest_validation_rejects_inconsistent_action_permission(self):
        """Fail-fast when an action permission does not match <key>.<action>."""
        with self.assertRaises(ValueError) as ctx:
            AppManifest(
                key="sample",
                name="Sample",
                description="Test.",
                url_name="sample:index",
                access_permission="sample.access",
                actions=[
                    AppAction(key="approve", permission="other.approve", label="Approve"),
                ],
            )
        self.assertIn("permission", str(ctx.exception))

    def test_manifest_validation_rejects_bad_url_name(self):
        """Fail-fast when the URL reference is not namespaced."""
        with self.assertRaises(ValueError) as ctx:
            AppManifest(
                key="sample",
                name="Sample",
                description="Test.",
                url_name="sample-index",
                access_permission="sample.access",
            )
        self.assertIn("url_name", str(ctx.exception))

    def tearDown(self):
        registry.reset()
