from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AppRegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.app_registry"
    label = "core_app_registry"
    verbose_name = "App Registry"

    def ready(self):
        from core.app_registry.services import sync_app_permissions

        def _sync(sender, **kwargs):
            sync_app_permissions()

        post_migrate.connect(_sync, sender=self)
