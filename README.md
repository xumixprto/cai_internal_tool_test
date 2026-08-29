# Internal Tools Platform

A prototype for a reusable internal tools platform built with Django.

Milestone 4 adds shared frontend and backend primitives usable by future business
applications:

- typed action permissions (`AppAction`) in the manifest
- authorization decorators and class-based mixins for app access and actions
- the `/apps/<app-key>/` URL convention
- app-aware breadcrumbs
- shared frontend components (headers, cards, tables, filters, pagination, forms, modals, alerts, badges, empty states)
- shared backend primitives (`TimestampedModel`, `AuditLog`, `Comment`, `Assignment`, `StatusHistory`)
- a developer-only `/dev/components/` showcase

No real business applications exist yet; the Dashboard correctly shows
`Applications: 0` until one is registered.

---

## Architecture

```text
internal_tools/
├── core/            # Reusable platform capabilities
│   ├── app_registry # In-memory registry and permission sync
│   ├── rbac         # Roles, permissions, decorators, mixins
│   ├── navigation   # Registry-driven nav and breadcrumbs
│   └── admin_panel  # Platform admin UI
├── shared/          # Reusable domain-neutral models and services
├── apps/            # Individual business applications
└── templates/       # Shared platform templates and components
```

### `core/`

Platform capabilities such as navigation, authentication, RBAC, admin panel,
and the App Registry.

### `app_registry`

- `AppManifest` is a frozen dataclass describing a business app.
- `AppAction` describes an action permission (e.g. `approve`, `reject`).
- `registry` is a module-level in-memory registry.
- `sync_app_permissions()` creates or updates the Django `Permission` objects
  declared by each manifest and grants the `Admin` group all of them.
- `apps_for_user(user)` returns the visible manifests a user may access.
- `set_user_app_access(user, app_keys, action_permissions)` updates only
  registry-managed permissions while preserving unrelated permissions and
  permissions belonging to other apps.

### `shared/`

Reusable domain-neutral utilities, base models, and services that any business
application may use. Current primitives are in `shared/models/primitives.py`
and `shared/services/primitives.py`.

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

### URL convention

All business apps live under `/apps/<app-key>/`:

```text
/apps/refunds/
/apps/refunds/123/
/apps/kyc/
/apps/kyc/123/
```

Each app still owns its `urls.py` and Django URL namespace. Manifests use named
routes rather than hardcoded paths:

```python
# config/urls.py
path("apps/refunds/", include("apps.refunds.urls"))

# apps/refunds/urls.py
app_name = "refunds"
urlpatterns = [path("", views.index, name="index")]

# apps/refunds/manifest.py
AppManifest(
    key="refunds",
    url_name="refunds:index",
    ...
)
```

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
- Effective action authorization requires both the app access permission **and**
  the action permission.

### Programmatic checks

```python
from core.rbac.services import is_admin, can, can_access_app, can_perform_action

if is_admin(request.user):
    ...

if can_access_app(request.user, "refunds"):
    ...

if can_perform_action(request.user, "refunds", "approve"):
    ...

if can(request.user, "refunds.approve"):
    ...
```

### Route-level app authorization

```python
from core.rbac.decorators import require_app_access, require_app_action


@require_app_access("refunds")
def index(request): ...


@require_app_action("refunds", "approve")
def approve(request): ...
```

Anonymous users are redirected to `/login/`; authenticated users without
permission receive `403`.

### Class-based view authorization

```python
from core.rbac.mixins import AppAccessRequiredMixin, AppActionRequiredMixin


class RefundListView(AppAccessRequiredMixin, ListView):
    app_key = "refunds"


class RefundApproveView(AppActionRequiredMixin, View):
    app_key = "refunds"
    action_key = "approve"
```

---

## App Registry

The App Registry is the platform's source of truth for business applications.

Each future business application declares a `manifest.py` and registers it from
`apps.py`:

```python
# apps/refunds/manifest.py
from core.app_registry.manifest import AppAction, AppManifest

manifest = AppManifest(
    key="refunds",
    name="Refund Review",
    description="Review and process refund requests.",
    icon="credit-card",
    url_name="refunds:index",
    access_permission="refunds.access",
    actions=[
        AppAction(key="approve", permission="refunds.approve", label="Approve"),
        AppAction(key="reject", permission="refunds.reject", label="Reject"),
    ],
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

`AppManifest` accepts `actions` as `AppAction` objects, a dict, or a list of
dicts. They are normalized to a tuple of `AppAction` instances during validation.

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

Application access is generated dynamically from the registry. For each app,
Admins see:

```text
[x] Application Access

Actions
[x] Approve
[ ] Reject
```

The UI never hardcodes app or action names. When saving, the form updates **only**
permissions managed by registered apps, preserves unrelated Django permissions,
preserves other apps' permissions, and never uses `user.user_permissions.clear()`.

Admins automatically receive all registered app and action permissions through
`sync_app_permissions`.

---

## Navigation and Dashboard

The sidebar and Dashboard application cards are generated from the registry.

- `Dashboard` and `Admin` are core navigation entries.
- Business applications appear under an **Applications** section, sorted by
  `order` then by name/key.
- The Dashboard **Applications** stat is `apps_for_user(request.user)` count.
- Breadcrumbs are built from the App Registry using `app_breadcrumbs()` rather
  than by parsing URLs.

When no business apps are registered, the Dashboard correctly shows
`Applications: 0` and an empty state.

---

## Frontend primitives

Shared template components are in `templates/components/`. They use Bootstrap 5
and standard Django templates plus the `platform_extras` template tags
(`add_class`, `widget_class`).

| Component | Example |
|-----------|---------|
| `page_header.html` | `{% include "components/page_header.html" with title="Requests" description="List" %}` |
| `card.html` | `{% include "components/card.html" with title="Summary" body="..." %}` |
| `button.html` | `{% include "components/button.html" with label="Save" style="primary" %}` |
| `badge.html` | `{% include "components/badge.html" with label="Pending" style="warning" %}` |
| `table.html` | `{% include "components/table.html" with headers=headers rows=rows action_column=True safe=True %}` |
| `empty_state.html` | `{% include "components/empty_state.html" with message="No items." %}` |
| `alert.html` | `{% include "components/alert.html" with message="Saved." style="success" %}` |
| `messages.html` | `{% include "components/messages.html" %}` renders Django messages |
| `form_field.html` | `{% include "components/form_field.html" with field=form.name %}` |
| `text_field.html` | standalone text `<input>` |
| `textarea.html` | standalone `<textarea>` |
| `select.html` | standalone `<select>` |
| `checkbox.html` | standalone checkbox input |
| `date_input.html` | standalone date `<input>` |
| `search_input.html` | standalone search input |
| `filter_bar.html` | search/status/date filter layout |
| `pagination.html` | `{% include "components/pagination.html" with page_obj=page_obj %}` |
| `confirmation_modal.html` | reusable Bootstrap modal |
| `detail_section.html` | label/value detail rows |

`form_field.html` works with Django form fields, including labels, errors, help
text, required indicators, and widget class mapping.

The shared table provides headers, row styling, an empty state, responsive
overflow, and an optional action column. Business apps still control their row
markup by passing HTML strings when `safe=True`.

`filter_bar.html` uses GET parameters and supports optional HTMX attributes.

---

## App-aware breadcrumbs

Views build breadcrumbs from registry data with `app_breadcrumbs()`:

```python
from core.navigation.breadcrumbs import app_breadcrumbs

breadcrumbs = app_breadcrumbs(
    app_key="refunds",
    object_label="Refund #101",
    object_url="",
)
# -> [Dashboard, Refund Review, Refund #101]
```

The shell `breadcrumbs.html` template renders `breadcrumbs` and falls back to
`page_title`.

---

## Backend primitives

`shared/models/primitives.py` provides domain-neutral models all future apps can
use:

| Primitive | Purpose |
|-----------|---------|
| `TimestampedModel` | Abstract base with `created_at` / `updated_at` |
| `AuditLog` | Append-only operational audit trail |
| `Comment` | Plain-text notes attached to any object |
| `Assignment` | Assignment history; latest is current |
| `StatusHistory` | Status transition history |

All object-linked primitives inherit `GenericObjectReference`, a reusable
`ContentType` / `GenericForeignKey` pattern with a single composite index on
`(content_type, object_id)`.

Services are in `shared/services/primitives.py`:

```python
from shared.services.primitives import audit, comments, assignments, status_history

# Audit
audit.log(
    actor=user,
    app_key="refunds",
    action="refund.approved",
    obj=refund,
    metadata={"amount": "120.00"},
)

# Comments
comments.add(obj=refund, author=user, body="Customer confirmed charge.")
comments.for_object(refund)

# Assignments
assignments.assign(obj=item, assigned_to=user1, assigned_by=admin)
assignments.current_for(item)
assignments.history_for(item)

# Status transitions
status_history.record(
    obj=item,
    new_status="Approved",
    previous_status="Pending",
    actor=user,
    note="Approved by manager",
)
status_history.latest_for(item)
status_history.for_object(item)
```

Actors use `SET_NULL`; deleting a user does not delete audit history or other
records.

Multi-step business mutations should be wrapped in `transaction.atomic()` by the
caller when consistency matters:

```python
from django.db import transaction

with transaction.atomic():
    item.status = "approved"
    item.save()
    status_history.record(obj=item, new_status="Approved", previous_status="Pending", actor=user)
    audit.log(actor=user, app_key="refunds", action="approved", obj=item)
```

---

## Developer component showcase

A developer-only page at `/dev/components/` renders examples of every shared
component.

```text
DEBUG=True + Admin  -> accessible
Normal User         -> 403
DEBUG=False         -> 404
```

The page is not shown in normal navigation. Login with the seeded `admin/admin`
credentials and navigate to [http://127.0.0.1:8000/dev/components/](http://127.0.0.1:8000/dev/components/).

---

## Seeding demo users

```bash
python manage.py seed_demo_users
```

The command is idempotent. It creates the `Admin` and `User` groups, ensures the
demo accounts exist, and synchronizes app permissions so `Admin` receives all
registered app and action permissions.

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

Milestone 4 delivers:

- `AppAction` typed action permissions in `AppManifest`
- `require_app_action` decorator and `AppActionRequiredMixin`
- `AppAccessRequiredMixin` for class-based views
- `can_perform_action()` requiring app access + action permission
- `/apps/<app-key>/` URL convention documented
- `app_breadcrumbs()` using App Registry data
- Admin user-access UI with per-app and per-action checkboxes
- Preservation of unrelated and cross-app permissions on save
- Shared backend primitives (`TimestampedModel`, `AuditLog`, `Comment`,
  `Assignment`, `StatusHistory`) with generic object references
- Shared frontend components for tables, filters, pagination, forms, messages,
  badges, alerts, modals, and detail sections
- `/dev/components/` developer showcase with admin-only access
- Comprehensive tests for authorization, admin permissions, backend primitives,
  and the component showcase
- Updated README documenting frontend/backend primitives, authorization helpers,
  and URL convention

## Future milestones

Later work will add:

- Real business apps (Refund Review, KYC Review, Vendor Approval, etc.)
- Provider integrations (payment APIs, document APIs)
- Production SSO
