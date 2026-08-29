from django.apps import AppConfig


class RefundsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.refunds"
    label = "refunds"

    def ready(self):
        from core.app_registry import registry

        from .manifest import manifest

        registry.register(manifest)
