"""Scaffold a new internal business application following platform conventions."""

import keyword
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.app_registry import AppAction, AppManifest, registry

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _python_class_name(key: str) -> str:
    """Return a CamelCase Python class name for an app key."""
    return "".join(part.capitalize() or "_" for part in key.split("_"))


def _label_for(action: str) -> str:
    """Return a human-readable label for an action key."""
    return action.replace("_", " ").strip().title()


class Command(BaseCommand):
    """Create apps/<key>/ with the standard business-app layout."""

    help = "Scaffold a new business application under apps/<key>/"

    def add_arguments(self, parser):
        parser.add_argument("key", help="Unique app key (e.g. feature_flags)")
        parser.add_argument(
            "--name",
            default=None,
            help='Human-readable app name (default: "Feature Flags" from key)',
        )
        parser.add_argument(
            "--actions",
            nargs="*",
            default=[],
            help="Optional action keys (e.g. --actions enable disable)",
        )
        parser.add_argument(
            "--no-url-mount",
            action="store_true",
            help="Do not modify config/urls.py; print the required include line instead.",
        )

    def handle(self, key, name, actions, no_url_mount, **options):
        if keyword.iskeyword(key):
            raise CommandError(f"'{key}' is a reserved Python keyword.")
        if not _KEY_RE.match(key):
            raise CommandError(
                f"Invalid app key '{key}': must match {_KEY_RE.pattern} and use lower-case names."
            )

        if registry.contains(key):
            raise CommandError(
                f"An app with key '{key}' is already registered in the App Registry."
            )

        apps_dir = Path(settings.BASE_DIR) / "apps"
        app_dir = apps_dir / key
        if app_dir.exists():
            raise CommandError(
                f"Directory {app_dir.relative_to(settings.BASE_DIR)} already exists. "
                "Remove it first or choose a different key."
            )

        app_name = name or _label_for(key)
        class_name = _python_class_name(key)
        action_objects = self._build_actions(key, actions)

        manifest = AppManifest(
            key=key,
            name=app_name,
            description=f"{app_name} internal tool.",
            icon="app",
            url_name=f"{key}:index",
            access_permission=f"{key}.access",
            actions=tuple(action_objects),
        )

        app_dir.mkdir(parents=True)
        self._write_files(app_dir, key, app_name, class_name, manifest, action_objects)

        mounted = False
        if not no_url_mount:
            mounted = self._try_mount_url(key)

        self._print_summary(app_dir, key, app_name, mounted)

    def _build_actions(self, app_key: str, action_keys: list[str]) -> list[AppAction]:
        """Validate action keys and return AppAction instances."""
        actions = []
        for action_key in action_keys:
            if not _KEY_RE.match(action_key):
                raise CommandError(
                    f"Invalid action key '{action_key}': must match {_KEY_RE.pattern}"
                )
            if action_key == "access":
                raise CommandError("Action key 'access' is reserved.")
            actions.append(
                AppAction(
                    key=action_key,
                    permission=f"{app_key}.{action_key}",
                    label=_label_for(action_key),
                    order=100,
                )
            )
        return actions

    def _write_files(self, app_dir, key, app_name, class_name, manifest, action_objects):
        """Generate the standard business-app files."""
        context = {
            "key": key,
            "app_name": app_name,
            "class_name": class_name,
            "manifest_actions": self._manifest_actions_literal(action_objects),
        }

        files = {
            "__init__.py": "",
            "apps.py": _APPS_PY_TEMPLATE.format(**context),
            "manifest.py": _MANIFEST_PY_TEMPLATE.format(
                **context, description=manifest.description
            ),
            "urls.py": _URLS_PY_TEMPLATE.format(**context),
            "views.py": _VIEWS_PY_TEMPLATE.format(**context),
            "forms.py": _FORMS_PY_TEMPLATE.format(**context),
            "models/__init__.py": _MODELS_INIT_TEMPLATE.format(**context),
            "services/__init__.py": _SERVICES_INIT_TEMPLATE.format(**context),
            "providers/__init__.py": _PROVIDERS_INIT_TEMPLATE.format(**context),
            f"templates/{key}/index.html": _INDEX_HTML_TEMPLATE.format(**context),
            "tests/__init__.py": _TESTS_INIT_TEMPLATE.format(**context),
            "tests/test_views.py": _TEST_VIEWS_TEMPLATE.format(**context),
        }

        for relative_path, content in files.items():
            path = app_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def _manifest_actions_literal(self, action_objects: list[AppAction]) -> str:
        """Return a Python literal for the manifest actions field."""
        if not action_objects:
            return "()"
        lines = "[\n"
        for action in action_objects:
            lines += (
                f'        AppAction(key="{action.key}", '
                f'permission="{action.permission}", '
                f'label="{action.label}"),\n'
            )
        lines += "    ]"
        return lines

    def _try_mount_url(self, key: str) -> bool:
        """Insert the app's URL include into config/urls.py if possible."""
        urls_file = Path(settings.BASE_DIR) / "config" / "urls.py"
        if not urls_file.exists():
            return False

        lines = urls_file.read_text().splitlines(keepends=True)
        try:
            insert_at = self._find_url_insert_point(lines)
        except LookupError:
            return False

        include_line = f'    path("apps/{key}/", include("apps.{key}.urls")),\n'
        if include_line in lines:
            return True

        lines.insert(insert_at, include_line)
        urls_file.write_text("".join(lines))
        return True

    def _find_url_insert_point(self, lines: list[str]) -> int:
        """Return the line index before the closing bracket of urlpatterns."""
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped in ("]", "],"):
                return i
        raise LookupError("Could not find urlpatterns closing bracket")

    def _print_summary(self, app_dir, key, app_name, mounted):
        rel = app_dir.relative_to(settings.BASE_DIR)
        self.stdout.write(self.style.SUCCESS(f"Created {rel}/"))
        self.stdout.write("")
        self.stdout.write(f"App name: {app_name}")
        self.stdout.write(f"Key:      {key}")
        self.stdout.write("")
        self.stdout.write("Next steps:")
        self.stdout.write(f"  1. Add 'apps.{key}' to INSTALLED_APPS in config/settings/base.py")
        if not mounted:
            self.stdout.write("  2. Add this line to config/urls.py urlpatterns:")
            self.stdout.write(f'        path("apps/{key}/", include("apps.{key}.urls")),')
        else:
            self.stdout.write("  2. config/urls.py has been updated automatically.")
        self.stdout.write(f"  3. python manage.py makemigrations {key}")
        self.stdout.write("  4. python manage.py sync_app_permissions")
        self.stdout.write(f"  5. Grant '{key}.access' through Platform Admin")
        self.stdout.write("")
        self.stdout.write("When you add domain models, put business rules in services/ and")
        self.stdout.write("external integration stubs in providers/.")


_APPS_PY_TEMPLATE = '''\
"""Django application configuration for {app_name}."""

from django.apps import AppConfig


class {class_name}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{key}"
    label = "{key}"
    verbose_name = "{app_name}"

    def ready(self):
        from core.app_registry import registry

        from .manifest import manifest

        registry.register(manifest)
'''


_MANIFEST_PY_TEMPLATE = '''\
"""App manifest for {app_name}."""

from core.app_registry import AppAction, AppManifest


manifest = AppManifest(
    key="{key}",
    name="{app_name}",
    description="{description}",
    icon="app",
    url_name="{key}:index",
    access_permission="{key}.access",
    actions={manifest_actions},
    order=100,
)
'''


_URLS_PY_TEMPLATE = '''\
"""URL configuration for {app_name}."""

from django.urls import path

from . import views

app_name = "{key}"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
]
'''


_VIEWS_PY_TEMPLATE = '''\
"""Views for {app_name}."""

from django.views.generic import TemplateView

from core.rbac.mixins import AppAccessRequiredMixin


class IndexView(AppAccessRequiredMixin, TemplateView):
    """Starter page for the {app_name} app."""

    app_key = "{key}"
    template_name = "{key}/index.html"
    extra_context = {{"page_title": "{app_name}"}}
'''


_FORMS_PY_TEMPLATE = '''\
"""Forms for {app_name}."""
'''


_MODELS_INIT_TEMPLATE = '''\
"""Domain models for {app_name}."""
'''


_SERVICES_INIT_TEMPLATE = '''\
"""Business services for {app_name}."""
'''


_PROVIDERS_INIT_TEMPLATE = '''\
"""External/provider integrations for {app_name}."""
'''


_TESTS_INIT_TEMPLATE = '''\
"""Tests for {app_name}."""
'''


_INDEX_HTML_TEMPLATE = """\
{{% extends "shell/app_shell.html" %}}

{{% block app_content %}}
<div class="d-flex justify-content-between align-items-start mb-4">
  <h1 class="h3">{app_name}</h1>
</div>
<div class="alert alert-info">
  <p class="mb-0">
    Welcome to <strong>{app_name}</strong>. This is the starter page generated by
    the <code>create_internal_app</code> scaffold.
  </p>
</div>
{{% endblock %}}
"""


_TEST_VIEWS_TEMPLATE = '''\
"""Authorization baseline tests for {app_name}."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.app_registry import registry

User = get_user_model()


class {class_name}AccessTests(TestCase):
    """Verify the app is registered and protected by RBAC."""

    @classmethod
    def setUpTestData(cls):
        from apps.{key}.manifest import manifest

        registry.register(manifest)
        call_command("sync_app_permissions")

        cls.access_url = reverse("{key}:index")

        cls.user_with_access = User.objects.create_user(
            username="{key}_user", password="pw"
        )
        cls.user_without_access = User.objects.create_user(
            username="{key}_other", password="pw"
        )

        from core.app_registry.services import set_user_app_access

        set_user_app_access(cls.user_with_access, {{"{key}"}})

    def test_manifest_is_registered(self):
        keys = [m.key for m in registry.all()]
        self.assertIn("{key}", keys)

    def test_index_url_resolves(self):
        self.assertEqual(self.access_url, "/apps/{key}/")

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(self.access_url)
        self.assertEqual(response.status_code, 302)

    def test_user_without_access_gets_403(self):
        self.client.login(username="{key}_other", password="pw")
        response = self.client.get(self.access_url)
        self.assertEqual(response.status_code, 403)

    def test_user_with_access_gets_200(self):
        self.client.login(username="{key}_user", password="pw")
        response = self.client.get(self.access_url)
        self.assertEqual(response.status_code, 200)

    def test_admin_gets_200(self):
        from django.contrib.auth.models import Group

        admin = User.objects.create_user(username="{key}_admin", password="pw")
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        admin.groups.add(admin_group)
        self.client.login(username="{key}_admin", password="pw")
        response = self.client.get(self.access_url)
        self.assertEqual(response.status_code, 200)
'''
