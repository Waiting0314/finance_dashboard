from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    Custom user model inheriting from AbstractUser.
    We will use the `is_active` field to manage email verification.
    A user is created with `is_active=False` and becomes active
    only after clicking the verification link in their email.
    """
    pass