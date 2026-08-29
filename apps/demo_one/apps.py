from django.apps import AppConfig


class DemoOneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.demo_one"
    label = "demo_one"
    verbose_name = "Demo App One"
