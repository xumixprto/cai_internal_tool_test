from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.rbac"
    label = "core_rbac"
    verbose_name = "RBAC"
