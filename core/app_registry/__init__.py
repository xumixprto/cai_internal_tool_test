"""App Registry for the Internal Tools Platform.

Business applications register AppManifest instances from their
AppConfig.ready() methods.  The registry is the source of truth for
navigation, dashboard cards, and permission synchronization.
"""

from core.app_registry.manifest import AppAction, AppManifest
from core.app_registry.registry import AppRegistry, registry

__all__ = ["AppAction", "AppManifest", "AppRegistry", "registry"]
