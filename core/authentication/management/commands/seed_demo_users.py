from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.app_registry.services import sync_app_permissions
from core.rbac.roles import Role


class Command(BaseCommand):
    """Seed the three demo accounts required by the local prototype.

    The credentials are intentionally insecure and exist only for development.
    """

    help = "Create demo users, platform roles, and app permissions for local development."

    def handle(self, *args, **options):
        User = get_user_model()

        admin_group, _ = Group.objects.get_or_create(name=Role.ADMIN.value)
        user_group, _ = Group.objects.get_or_create(name=Role.USER.value)

        # Synchronize all registered application permissions and assign
        # them to the Admin group.
        sync_app_permissions()

        users = [
            {
                "username": "admin",
                "password": "admin",
                "first_name": "",
                "group": admin_group,
                "is_active": True,
            },
            {
                "username": "user1",
                "password": "user1",
                "first_name": "",
                "group": user_group,
                "is_active": True,
            },
            {
                "username": "user2",
                "password": "user2",
                "first_name": "",
                "group": user_group,
                "is_active": True,
            },
        ]

        for spec in users:
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "first_name": spec["first_name"],
                    "is_active": spec["is_active"],
                },
            )
            user.set_password(spec["password"])
            user.is_active = spec["is_active"]
            user.save()

            user.groups.clear()
            user.groups.add(spec["group"])

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} {user.username}")

        self.stdout.write(self.style.SUCCESS("Demo users seeded successfully."))
