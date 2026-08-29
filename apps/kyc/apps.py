from django.apps import AppConfig


class KycConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kyc"
    label = "kyc"

    def ready(self):
        from core.app_registry import registry

        from .manifest import manifest

        registry.register(manifest)
