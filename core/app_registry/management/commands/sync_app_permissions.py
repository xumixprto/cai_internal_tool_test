from django.core.management.base import BaseCommand

from core.app_registry.services import sync_app_permissions


class Command(BaseCommand):
    """Synchronize registered application permissions with Django's auth tables."""

    help = "Create Permissions and ContentTypes for all registered app manifests."

    def handle(self, *args, **options):
        sync_app_permissions()
        self.stdout.write(self.style.SUCCESS("Application permissions synchronized."))
