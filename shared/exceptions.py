"""Shared exceptions for the platform."""


class InternalToolsError(Exception):
    """Base exception for the platform."""

    pass


class ServiceError(InternalToolsError):
    """Raised by business services."""

    pass


class ProviderError(InternalToolsError):
    """Raised by provider integrations."""

    pass
