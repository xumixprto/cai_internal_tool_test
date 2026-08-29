from django.apps import AppConfig


class DemoTwoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.demo_two"
    label = "demo_two"
    verbose_name = "Demo App Two"
