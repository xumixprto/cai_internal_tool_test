from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for the Internal Tools Platform.

    Extending AbstractUser now avoids a difficult migration away from the
    default Django User later.
    """

    class Meta:
        swappable = "AUTH_USER_MODEL"
        permissions = [
            ("access_admin", "Can access platform admin"),
        ]
