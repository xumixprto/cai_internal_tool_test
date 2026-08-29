"""Tests for the create_internal_app management command."""

import importlib.util
import py_compile
import sys
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class CreateInternalAppScaffoldTests(TestCase):
    """Verify the scaffold produces valid, well-structured business apps."""

    def test_valid_app_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps").mkdir(parents=True)
            with self.settings(BASE_DIR=Path(temp)):
                call_command(
                    "create_internal_app",
                    "feature_flags",
                    "--name=Feature Flags",
                    "--actions=enable",
                    "--actions=disable",
                    "--no-url-mount",
                )

            app_dir = Path(temp) / "apps" / "feature_flags"
            self.assertTrue(app_dir.exists())

            expected_files = [
                "__init__.py",
                "apps.py",
                "manifest.py",
                "urls.py",
                "views.py",
                "forms.py",
                "models/__init__.py",
                "services/__init__.py",
                "providers/__init__.py",
                "templates/feature_flags/index.html",
                "tests/__init__.py",
                "tests/test_views.py",
            ]
            for relative in expected_files:
                self.assertTrue((app_dir / relative).exists(), f"{relative} missing")

    def test_generated_python_compiles(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps").mkdir(parents=True)
            with self.settings(BASE_DIR=Path(temp)):
                call_command(
                    "create_internal_app",
                    "health_checks",
                    "--no-url-mount",
                )

            for path in (Path(temp) / "apps" / "health_checks").rglob("*.py"):
                py_compile.compile(str(path), doraise=True)

    def test_manifest_is_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps").mkdir(parents=True)
            with self.settings(BASE_DIR=Path(temp)):
                call_command(
                    "create_internal_app",
                    "inventory",
                    "--name=Inventory",
                    "--actions=restock",
                    stdout=open("/dev/null", "w"),
                )

            module_path = Path(temp) / "apps" / "inventory" / "manifest.py"
            manifest = self._load_manifest_from(module_path, "apps.inventory.manifest")
            self.assertEqual(manifest.key, "inventory")
            self.assertEqual(manifest.access_permission, "inventory.access")
            self.assertEqual(len(manifest.actions), 1)
            self.assertEqual(manifest.actions[0].key, "restock")

    def test_duplicate_app_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps").mkdir(parents=True)
            with self.settings(BASE_DIR=Path(temp)):
                call_command("create_internal_app", "first_app", "--no-url-mount")
                with self.assertRaises(CommandError) as ctx:
                    call_command("create_internal_app", "first_app", "--no-url-mount")
                self.assertIn("already exists", str(ctx.exception))

    def test_invalid_key_rejected(self):
        invalid_keys = ["123bad", "Bad-Key", "my app", "class"]
        for key in invalid_keys:
            with self.assertRaises(CommandError) as ctx:
                call_command("create_internal_app", key, "--no-url-mount")
            self.assertTrue(
                "Invalid app key" in str(ctx.exception)
                or "reserved Python keyword" in str(ctx.exception),
                str(ctx.exception),
            )

    def test_url_mount(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps").mkdir(parents=True)
            config_dir = Path(temp) / "config"
            config_dir.mkdir()
            urls_file = config_dir / "urls.py"
            urls_file.write_text(
                "from django.urls import path, include\n"
                "urlpatterns = [\n"
                '    path("apps/existing/", include("apps.existing.urls")),\n'
                "]\n"
            )

            with self.settings(BASE_DIR=Path(temp)):
                call_command("create_internal_app", "new_app")

            content = urls_file.read_text()
            self.assertIn('path("apps/new_app/", include("apps.new_app.urls"))', content)

    def test_no_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "apps" / "existing").mkdir(parents=True)
            (Path(temp) / "apps" / "existing" / "__init__.py").write_text("")
            with self.assertRaises(CommandError) as ctx:
                with self.settings(BASE_DIR=Path(temp)):
                    call_command("create_internal_app", "existing", "--no-url-mount")
            self.assertIn("already exists", str(ctx.exception))

    def _load_manifest_from(self, path: Path, dotted_name: str):
        """Load a generated manifest module without polluting sys.modules."""
        spec = importlib.util.spec_from_file_location(dotted_name, str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(dotted_name, None)
        return module.manifest
