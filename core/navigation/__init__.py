"""Centralized navigation for the Internal Tools Platform."""

from core.navigation.breadcrumbs import app_breadcrumbs, simple_breadcrumbs
from core.navigation.registry import CORE_NAV_ITEMS, get_nav_items

__all__ = [
    "CORE_NAV_ITEMS",
    "app_breadcrumbs",
    "get_nav_items",
    "simple_breadcrumbs",
]
