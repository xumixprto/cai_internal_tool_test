# Internal Tools Platform

A prototype for a reusable internal tools platform built with Django.

Milestone 2 adds authentication, a custom user model, role-based access control,
protected routes, and a platform administration panel.

---

## Architecture

```text
internal_tools/
├── core/        # Reusable platform capabilities
├── shared/      # Reusable code not tied to one business domain
├── apps/        # Individual business applications
└── templates/   # Shared platform templates
```

### `core/`

Platform capabilities such as navigation, authentication, RBAC, admin panel,
audit logging placeholders, and primitives.

### `shared/`

Reusable utilities, base models, service/provider base classes, exceptions, and
formatting helpers that any business application may use.

### `apps/`

Individual business applications. The Milestone 1 demo applications have been
removed; real apps will be added in later milestones.

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
├── models/        # Persistent domain entities
├── services/      # Business operations and rules
├── providers/     # External system abstractions
├── views/         # Thin HTTP layer
├── templates/     # App-specific templates
└── urls.py        # App URL configuration
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

# Seed the demo users
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
| `Admin` | Platform administrator; can access `/platform-admin/` and manage users. |
| `User` | Standard platform user; can access the Dashboard only. |

Roles are stored as Django Groups. The seeded `admin` account is a platform
admin. `user1` and `user2` are standard users by default.

### Permissions

The platform-wide permission `core_authentication.access_admin` guards access to
the custom admin panel. Future business applications will add their own
permissions (for example, `refunds.access`, `kyc.access`) once the App Registry is
implemented.

### Programmatic checks

```python
from core.rbac.services import is_admin, has_permission

if is_admin(request.user):
    ...

if has_permission(request.user, "refunds.access"):
    ...
```

---

## Admin panel

The custom platform admin panel is at `/platform-admin/` and uses the same shell
as the rest of the platform. It lists users and lets an Admin change the role and
active status of `user1` and `user2`. The seeded `admin` account is shown as
read-only and cannot be edited through the panel.

---

## Seeding demo users

```bash
python manage.py seed_demo_users
```

The command is idempotent. It creates the `Admin` and `User` groups, assigns the
`access_admin` permission to the `Admin` group, and ensures the three demo
accounts exist with their default role and active status. Running it multiple
times will not create duplicates; it will reset the demo passwords back to
their known values.

---

## Testing

```bash
python manage.py test
```

---

## Linting

```bash
ruff check .
ruff format .
```

---

## Current milestone

Milestone 2 delivers:

- Custom `User` model extending `AbstractUser`
- Login/logout with session authentication
- Protected routes that redirect anonymous users to `/login/`
- Django Group-based RBAC with centralized helpers in `core/rbac/`
- `Admin` and `User` platform roles
- Role-aware navigation (Admin entry shown only to admins)
- Custom `/platform-admin/` panel for user access management
- Demo user seeding command (`python manage.py seed_demo_users`)
- CSRF-protected POST endpoints for access changes
- 403 error page for unauthorized access
- Updated tests covering authentication, RBAC, and admin panel security
- Ruff configuration with migrations excluded

## Future milestones

Later work will add:

- App Registry based on per-app `manifest.py` files
- Real business apps (Refund Review, KYC Review, Vendor Approval, etc.)
- Per-application access management in the admin panel
- Audit logging
- Provider integrations (payment APIs, document APIs, identity providers)
- Production SSO
