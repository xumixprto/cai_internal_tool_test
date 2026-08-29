from enum import StrEnum


class Role(StrEnum):
    """Platform roles.  Persisted as Django Groups."""

    ADMIN = "Admin"
    USER = "User"
