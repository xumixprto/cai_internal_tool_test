# Internal Tools Platform

A prototype for a reusable internal tools platform built with Django.

This milestone establishes the architecture and shared application shell that
future business applications will reuse.

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

Platform capabilities such as navigation, app registry, authentication, RBAC,
audit logging, and primitives. For Milestone 1 most of these are placeholders,
but the package structure is in place.

### `shared/`

Reusable utilities, base models, service/provider base classes, exceptions, and
formatting helpers that any business application may use.

### `apps/`

Individual business applications. Each app owns its own models, services,
providers, views, templates, and URLs.

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

# Start the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

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

Milestone 1 delivers:

- Django project with clean `config/settings` separation
- `core/`, `shared/`, and `apps/` package layout
- A shared professional application shell (topbar, sidebar, breadcrumbs, main
  content)
- Centralized navigation in `core/navigation/`
- Dashboard landing page
- Two placeholder business apps (`demo_one`, `demo_two`) inside the same shell
- Reusable frontend components (page header, card, button, badge, empty state)
- Thin views delegating to services
- Service/provider separation for mock data
- HTMX and Bootstrap 5 included
- SQLite database
- `python manage.py runserver` local startup
- Basic tests and Ruff configuration

## Future milestones

Later work will add:

- Authentication and login flow
- RBAC and permission-aware navigation
- Demo users
- Real App Registry
- Shared frontend/backend primitives
- Audit logging
- Real business apps (Refund Review, KYC Review, Vendor Approval, etc.)
- Provider integrations (payment APIs, document APIs, identity providers)
- Production SSO
