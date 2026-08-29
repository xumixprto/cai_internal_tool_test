# Internal Tools Platform

A prototype for a reusable internal tools platform built with Django.

Milestone 3 adds a typed `AppManifest`, explicit per-app registration through
`AppConfig.ready()`, an in-memory App Registry, permission synchronization,
registry-driven navigation and dashboard, per-user application access in the
Admin panel, and reusable route-level app authorization.

---

## Architecture

```text
internal_tools/
├── core/            # Reusable platform capabilities
│   └── app_registry # In-memory registry and permission sync
├── shared/          # Reusable code not tied to one business domain
├── apps/            # Individual business applications
└── templates/       # Shared platform templates
```

### `core/`

Platform capabilities such as navigation, authentication, RBAC, admin panel,
and the App Registry.

### `app_registry`

- `AppManifest` is a frozen dataclass describing a business app.
- `registry` is a module-level in-memory registry.
- `sync_app_permissions()` creates or updates the Django `Permission` objects
  declared by each manifest and grants the `Admin` group all of them.
- `apps_for_user(user)` returns the visible manifests a user may access.

### `shared/`

Reusable utilities, base models, service/provider base classes, exceptions, and
formatting helpers that any business application may use.

### `apps/`

Individual business applications. There are no real business applications yet;
they will be added in later milestones. `apps/` currently contains only
`__init__.py` and `README.md`.

---

## Dependency rule

```text
core and shared must NOT import from individual business applications.
Business applications may import from core and shared.
```

This keeps the platform layer independent and reusable.

---

## Business application convention

Each app under `apps/` follows this structure:

```text
apps/<app_name>/
├── apps.py          # Django AppConfig
├── manifest.py      # Platform metadata
├── models/          # Persistent domain entities
├── services/        # Business operations and rules
├── providers/       # External system abstractions
├── views/           # Thin HTTP layer
├── templates/       # App-specific templates
└── urls.py          # App URL configuration
```

Views stay thin: they interpret the request, call a service, and render a
response. Business logic belongs in services.

---

## Development setup

Requires **Python 3.12+**.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python manage.py migrate

# Seed the demo users and synchronize app permissions
python manage.py seed_demo_users

# Start the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

---

## Demo credentials (local prototype only)

```text
admin / admin
user1 / user1
user2 / user2
```

These accounts are intentionally insecure and exist only for local development.

---

## Authentication

The platform uses Django session authentication with a login page at `/login/` and
logout via `/logout/`.

All platform routes require an authenticated user. Anonymous requests are
redirected to the login page.

---

## Custom User model

The project uses `core.authentication.models.User`, which extends Django's
`AbstractUser`. `AUTH_USER_MODEL` is set to `core_authentication.User`.

If the custom user model migrations cannot be applied because the local SQLite
database was created before this model, delete the `db.sqlite3` file and rerun:

```bash
python manage.py migrate
python manage.py seed_demo_users
```

---

## RBAC

Role-based access control is built on Django's `User`, `Group`, and
`Permission` models. The RBAC abstraction lives in `core/rbac/` and wraps the
Django APIs so business code does not hardcode group names or permission strings.

### Roles

| Role | Description |
|------|-------------|
| `Admin` | Platform administrator; can access `/platform-admin/`, manage users, and automatically has access to every registered business app. |
| `User` | Standard platform user; can access the Dashboard and any business apps granted to them individually. |

Roles are stored as Django Groups. The seeded `admin` account is a platform
admin. `user1` and `user2` are standard users by default.

### Permissions

- The platform-wide permission `core_authentication.access_admin` guards access to
  the custom admin panel.
- Each registered business app declares an app gateway permission such as
  `refunds.access`.
- Apps may also declare optional action permissions such as `refunds.approve`
  and `refunds.reject`.

### Programmatic checks

```python
from core.rbac.services import is_admin, can, can_access_app

if is_admin(request.user):
    ...

if can_access_app(request.user, "refunds"):
    ...

if can(request.user, "refunds.approve"):
    ...
```

### Route-level app authorization

```python
from core.rbac.decorators import require_app_access


@require_app_access("refunds")
def index(request): ...
```

Authenticated users without access receive `403`.

---

## App Registry

The App Registry is the platform's source of truth for business applications.

Each future business application declares a `manifest.py` and registers it from
`apps.py`:

```python
# apps/refunds/manifest.py
from core.app_registry.manifest import AppManifest

manifest = AppManifest(
    key="refunds",
    name="Refund Review",
    description="Review and process refund requests.",
    icon="credit-card",
    url_name="refunds:index",
    access_permission="refunds.access",
    actions={
        "approve": "refunds.approve",
        "reject": "refunds.reject",
    },
    order=100,
)

# apps/refunds/apps.py
from django.apps import AppConfig


class RefundsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.refunds"
    label = "refunds"

    def ready(self):
        from core.app_registry import registry
        from .manifest import manifest

        registry.register(manifest)
```

### Manifest lifecycle

```text
Django starts
    ↓
AppConfig.ready()
    ↓
manifest loaded
    ↓
registry.register(manifest)
    ↓
validated in-memory registry
```

Manifests are code-level configuration. The database stores users, groups,
permissions, and per-user access grants, but not the canonical list of
applications.

### Registering an app URL namespace

If a future app uses URLs, add the URLconf and include it in `config/urls.py`:

```python
# apps/refunds/urls.py
from django.urls import path
from . import views

app_name = "refunds"

urlpatterns = [
    path("", views.index, name="index"),
]

# config/urls.py
from django.urls import include, path

urlpatterns = [
    ...
    path("apps/refunds/", include("apps.refunds.urls")),
]
```

### Synchronizing permissions

After adding or changing a manifest, run:

```bash
python manage.py sync_app_permissions
```

This command is idempotent. It:

1. Inspects the App Registry.
2. Creates the app access permission and any action permissions.
3. Anchors them to per-app `ContentType(model="permission")` records.
4. Grants the `Admin` group all registered app permissions.

`sync_app_permissions` is also connected to `post_migrate` through
`core.app_registry`.

---

## Admin panel

The custom platform admin panel is at `/platform-admin/` and uses the same shell
as the rest of the platform. It lists users and lets an Admin change the role,
active status, and per-application access of `user1` and `user2`.

The seeded `admin` account is shown as read-only and cannot be edited through the
panel.

Application access is generated dynamically from the registry. With no apps
registered, the **Application Access** section correctly shows an empty state.

---

## Navigation and Dashboard

The sidebar and Dashboard application cards are generated from the registry.

- `Dashboard` and `Admin` are core navigation entries.
- Business applications appear under an **Applications** section, sorted by
  `order` then by name/key.
- The Dashboard **Applications** stat is `apps_for_user(request.user)` count.

When no business apps are registered, the Dashboard correctly shows
`Applications: 0` and an empty state.

---

## Seeding demo users

```bash
python manage.py seed_demo_users
```

The command is idempotent. It creates the `Admin` and `User` groups, ensures the
demo accounts exist, and synchronizes app permissions so `Admin` receives all
registered app permissions.

---

## Developer commands

```bash
python manage.py migrate              # apply migrations
python manage.py sync_app_permissions # create/update app permissions
python manage.py seed_demo_users      # create/reset demo accounts
python manage.py runserver            # start the dev server
```

`sync_app_permissions` is needed after adding a business app or changing its
permission set. The seed command calls it automatically.

---

## Testing

```bash
python manage.py test --settings=config.settings.test
```

---

## Linting

```bash
ruff check .
ruff format .
```

---

## Current milestone

Milestone 3 delivers:

- Typed `AppManifest` with validation
- In-memory `AppRegistry` with idempotent registration
- Explicit per-app manifest registration from `AppConfig.ready()`
- Permission synchronization (`sync_app_permissions`) for app access and action permissions
- `post_migrate` connection through `core.app_registry`
- RBAC helpers `can_access_app()` and `can()`
- `@require_app_access("key")` route decorator
- Registry-driven navigation and Dashboard application cards
- Per-user **Application Access** management in `/platform-admin/`
- `seed_demo_users` updates Admin permissions automatically
- Comprehensive tests using test-only manifests
- Updated README documenting the App Registry and manifest lifecycle

## Future milestones

Later work will add:

- Real business apps (Refund Review, KYC Review, Vendor Approval, etc.)
- Action-level permission administration UI
- Audit logging
- Provider integrations (payment APIs, document APIs)
- Production SSO
