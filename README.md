# Internal Tools Platform

A Django-based platform that hosts modular internal business applications behind a shared shell, navigation, and role-based access control. It currently ships with three real apps—**Refund Review**, **Vendor Approval**, and **KYC Review**—and a management command that scaffolds new apps in the same style.

## What it does

- Provides a single login, sidebar, and dashboard for all internal tools.
- Discovers business apps through an in-memory `AppRegistry` driven by per-app `manifest.py` files.
- Enforces per-app access and per-action permissions without any platform code knowing app-specific details.
- Keeps reusable UI, models, and services in `core/` and `shared/` while business logic lives in `apps/<app>/`.

## Core components

| Layer | Path | Purpose |
|-------|------|---------|
| Platform | `core/` | App registry (`core/app_registry/`), RBAC (`core/rbac/`), navigation (`core/navigation/`), admin panel (`core/admin_panel/`), authentication (`core/authentication/`). |
| Shared primitives | `shared/` | Domain-neutral models and services any app may reuse: `TimestampedModel`, `AuditLog`, `Comment`, `Assignment`, `StatusHistory`, plus `shared/services/primitives.py` and `shared/services/recording.py`. |
| Business apps | `apps/` | Refund Review, Vendor Approval, KYC Review, and any app you scaffold with `create_internal_app`. |
| Shared UI | `templates/` | Base shell, shared Bootstrap 5 components in `templates/components/`, and reusable page layouts. |

## Core commands

| Command | Purpose |
|---------|---------|
| `python manage.py migrate` | Apply database migrations. |
| `python manage.py seed_demo_users` | Create `admin`, `user1`, `user2` and synchronize permissions. |
| `python manage.py sync_app_permissions` | Create or update permissions declared in every app manifest. |
| `python manage.py create_internal_app <key>` | Scaffold a new business app under `apps/<key>/`. |
| `python manage.py runserver` | Start the development server. |
| `python manage.py test --settings=config.settings.test` | Run the test suite. |
| `ruff check .` | Lint the code. |
| `ruff format .` | Format the code. |

## Run it from scratch

Requires **Python 3.12+**.

```bash
# 1. Clone the repo and enter it
git clone <repo-url>
cd cai_internal_tool_test

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file
cp .env.example .env

# 5. Apply migrations
python manage.py migrate

# 6. Create demo users and sync permissions
python manage.py seed_demo_users

# 7. (Optional) Seed demo business data
python manage.py seed_refund_demo_data
python manage.py seed_vendor_demo_data
python manage.py seed_kyc_demo_data

# 8. Start the server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and log in with one of the demo accounts below.

## Demo credentials

```text
admin / admin   (platform admin)
user1 / user1   (standard user)
user2 / user2   (standard user)
```

These accounts are insecure and intended for local development only.

## Architecture rule

```text
core/ and shared/ must NOT import from apps/.
Business apps may import from core/ and shared/.
```

This keeps the platform independent from any single business workflow.

## Create a new internal app

The `create_internal_app` command at `core/management/commands/create_internal_app.py` generates a runnable app skeleton:

```bash
python manage.py create_internal_app feature_flags --name "Feature Flags" --actions enable disable
```

It produces:

```text
apps/feature_flags/
├── __init__.py
├── apps.py              # AppConfig; registers the manifest on startup
├── manifest.py          # AppManifest and optional AppAction permissions
├── urls.py              # App URLs mounted under /apps/feature_flags/
├── views.py             # Starter index view protected by app access
├── forms.py             # Empty form module
├── models/
├── services/
├── providers/
├── templates/feature_flags/
└── tests/               # Baseline auth tests
```

After scaffolding:

1. Add `"apps.feature_flags"` to `INSTALLED_APPS` in `config/settings/base.py`.
2. Run `python manage.py makemigrations feature_flags` and `python manage.py migrate`.
3. Run `python manage.py sync_app_permissions`.
4. Log in as `admin`, open `/platform-admin/`, and grant `feature_flags` access to a user.

See `BUILDING_APPS.md` for the full workflow.

## Reuse shared components

### Frontend components

Shared Django templates live in `templates/components/`:

```django
{% include "components/page_header.html" with title="Requests" subtitle="Review and approve" %}
{% include "components/table.html" with headers=headers rows=rows action_column=True safe=True %}
{% include "components/badge.html" with label="Approved" style="success" %}
{% include "components/pagination.html" with page_obj=page_obj %}
{% include "components/activity_timeline.html" with activity=activity %}
```

Available components include `page_header`, `table`, `badge`, `button`, `card`, `alert`, `form_field`, `filter_bar`, `pagination`, `detail_section`, `empty_state`, `confirmation_modal`, and `activity_timeline`.

### Backend primitives

Use `shared/services/primitives.py` for audit, comments, assignments, and status history:

```python
from shared.services.primitives import audit, comments, assignments, status_history

audit.log(actor=user, app_key="refunds", action="approved", obj=refund)
comments.add(obj=refund, author=user, body="Customer confirmed charge.")
assignments.assign(obj=refund, assigned_to=user, assigned_by=admin)
status_history.record(obj=refund, new_status="Approved", previous_status="Pending", actor=user)
```

For the common pattern of recording a change plus its audit event, use `shared/services/recording.py`:

```python
from shared.services.recording import record_status_change, record_assignment, record_note

record_status_change(
    obj=refund,
    previous_status="Pending",
    new_status="Approved",
    actor=user,
    app_key="refunds",
    action="approved",
)
```

## Testing and linting

```bash
python manage.py test --settings=config.settings.test
ruff check .
ruff format .
```

## App registry basics

Each app declares a manifest and registers it from `apps.py`:

```python
# apps/refunds/manifest.py
manifest = AppManifest(
    key="refunds",
    name="Refund Review",
    url_name="refunds:index",
    access_permission="refunds.access",
    actions=[
        AppAction(key="approve", permission="refunds.approve", label="Approve"),
    ],
)


# apps/refunds/apps.py
class RefundsConfig(AppConfig):
    name = "apps.refunds"

    def ready(self):
        from core.app_registry import registry
        from .manifest import manifest

        registry.register(manifest)
```

The registry drives the sidebar, dashboard, and admin access controls.
