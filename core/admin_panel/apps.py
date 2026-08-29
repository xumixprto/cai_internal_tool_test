from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.admin_panel"
    label = "core_admin_panel"
    verbose_name = "Admin Panel"
