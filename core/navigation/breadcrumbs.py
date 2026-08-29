"""App-aware breadcrumb helpers for the platform shell."""

from django.urls import reverse

from core.app_registry import registry


def app_breadcrumbs(
    app_key: str,
    object_label: str = "",
    object_url: str = "",
    extra: list[dict] | None = None,
) -> list[dict]:
    """Build a breadcrumb list from the App Registry and optional object data.

    The returned list always begins with ``Dashboard``.  If ``app_key`` is
    registered, the next crumb uses the app name and resolved manifest URL.
    Optional ``object_label``/``object_url`` and any ``extra`` items are
    appended after the app crumb.
    """
    breadcrumbs = [{"label": "Dashboard", "url": reverse("dashboard")}]

    try:
        manifest = registry.get(app_key)
        try:
            app_url = reverse(manifest.url_name)
        except Exception:
            app_url = ""
        breadcrumbs.append({"label": manifest.name, "url": app_url})
    except KeyError:
        pass

    if object_label:
        breadcrumbs.append({"label": object_label, "url": object_url or ""})

    if extra:
        breadcrumbs.extend(extra)

    return breadcrumbs


def simple_breadcrumbs(title: str, base_crumb: dict | None = None) -> list[dict]:
    """Return a minimal breadcrumb ending with an unlinked title."""
    breadcrumbs = [{"label": "Dashboard", "url": reverse("dashboard")}]
    if base_crumb:
        breadcrumbs.append(base_crumb)
    breadcrumbs.append({"label": title, "url": ""})
    return breadcrumbs
