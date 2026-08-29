"""Base class for external system integrations."""


class BaseProvider:
    """Providers abstract systems outside the application (e.g., APIs, files).

    Subclasses should be replaceable, mockable, and testable.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
