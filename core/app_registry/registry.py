"""In-memory registry for business application manifests."""

from core.app_registry.manifest import AppManifest


class AppRegistry:
    """Holds registered AppManifests for the duration of the process.

    Manifests are registered from each business application's
    AppConfig.ready() method.  The registry validates keys, prevents
    duplicate/overwriting registrations, and returns apps in a
    deterministic order.
    """

    def __init__(self):
        self._apps: dict[str, AppManifest] = {}

    def register(self, manifest: AppManifest) -> None:
        """Register a manifest or ignore if the exact same one is already registered."""
        if not isinstance(manifest, AppManifest):
            raise TypeError("Only AppManifest instances may be registered")

        existing = self._apps.get(manifest.key)
        if existing is not None:
            if existing == manifest:
                return
            raise ValueError(
                f"Application key '{manifest.key}' is already registered with a different manifest"
            )

        self._apps[manifest.key] = manifest

    def get(self, key: str) -> AppManifest:
        """Return the manifest for the given key."""
        if key not in self._apps:
            raise KeyError(f"No application registered with key '{key}'")
        return self._apps[key]

    def contains(self, key: str) -> bool:
        """Return True if a manifest with the given key is registered."""
        return key in self._apps

    def all(self) -> list[AppManifest]:
        """Return all registered manifests ordered by order, then name, then key."""
        return sorted(self._apps.values(), key=lambda m: (m.order, m.name, m.key))

    def reset(self) -> None:
        """Clear the registry.  Intended for tests only."""
        self._apps.clear()


# Global in-memory registry.  Business applications import this instance and
# call registry.register(manifest) from AppConfig.ready().
registry = AppRegistry()
