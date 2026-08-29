# Building Internal Apps

This guide describes how to add a new business application to the Internal Tools Platform.

## 1. Scaffold the app

```bash
python manage.py create_internal_app feature_flags --name "Feature Flags" --actions enable disable
```

This creates `apps/feature_flags/` with the standard layout:

```
apps/feature_flags/
├── __init__.py
├── apps.py              # AppConfig that registers the app manifest
├── manifest.py          # AppManifest + AppAction definitions
├── urls.py              # URLs mounted under /apps/feature_flags/
├── views.py             # AppAccessRequiredMixin-protected starter view
├── forms.py             # Empty form module
├── models/
├── services/
├── providers/
├── templates/feature_flags/
└── tests/
```

The command automatically inserts the include line into `config/urls.py` if it can do so safely and prints any remaining manual steps.

## 2. Register the app

If `create_internal_app` did not update `config/urls.py` automatically, add:

```python
(path("apps/feature_flags/", include("apps.feature_flags.urls")),)
```

Add the app to `INSTALLED_APPS` in `config/settings/base.py`:

```python
("apps.feature_flags",)
```

## 3. Define permissions

The scaffold generates:

- `feature_flags.access` automatically
- `feature_flags.enable` and `feature_flags.disable` if `--actions enable disable` was given

`manifest.py` is the single source of truth for the app's key, name, URL, access permission, and actions. The manifest is validated on construction (key format, namespaced `url_name`, `<key>.access` convention, action permission format).

## 4. Create domain models

Add model files under `apps/feature_flags/models/`.

- Extend `shared.models.TimestampedModel` for `created_at`/`updated_at`.
- Define `Status` and other choices as `TextChoices`/`IntegerChoices` in the model.
- Keep models thin; business rules live in `services/`.

## 5. Implement business rules in services

Add `apps/feature_flags/services/feature_flags.py`:

- Owns allowed state transitions and validation.
- Records status changes, assignments, and notes through `shared.services.recording` helpers.
- Calls external integrations through `providers/`.
- Raises app-specific error classes (for example, `FeatureFlagServiceError`).

```python
from shared.services.recording import record_status_change, record_assignment, record_note
```

## 6. Mock external integrations in providers

Add `apps/feature_flags/providers/feature_flag_provider.py`:

- Define a provider interface class.
- Provide a deterministic `Local<App>Provider` implementation for development and tests.
- Inject the provider into the service (`provider=None` optional argument).

## 7. Build views and templates

- Queue/list views extend `AppAccessRequiredMixin` and `ListView`.
- Actions extend `AppActionRequiredMixin` and `View`.
- Detail templates extend `shell/app_shell.html`.
- Reuse shared components: `page_header`, `form_field`, `table`, `pagination`, `activity_timeline`.

## 8. Create migrations and run sync

```bash
python manage.py makemigrations feature_flags
python manage.py migrate
python manage.py sync_app_permissions
```

`sync_app_permissions` creates the `feature_flags.access` permission (and any actions), assigns them to the Admin group, and refreshes the permission cache.

## 9. Grant access

Log in as `admin`/`admin`, go to **Admin > User Access**, and grant `feature_flags` to a non-admin user. Action permissions can be granted independently.

## 10. Add tests

The scaffold creates starter tests in `apps/feature_flags/tests/test_views.py` covering:

- manifest registration
- URL resolution
- anonymous redirect
- missing-access 403
- access-granted 200
- admin access 200

Add more tests for business rules, workflow transitions, and provider behavior in the same directory.

## 11. Add demo data (optional)

When it is useful, add a management command following the `seed_<app>_demo_data` naming convention:

```bash
python manage.py seed_feature_flags_demo_data
```

Make it idempotent and synthetic.

## Platform conventions

- URLs: `/apps/<key>/`
- Access permission: `<key>.access`
- Action permission: `<key>.<action>`
- Service error class: `<App>ServiceError`
- Provider interface: `<App>Provider`
- Local mock provider: `Local<App>Provider`
- Seed command: `seed_<app>_demo_data`
- `core/` and `shared/` never import from `apps/`.
