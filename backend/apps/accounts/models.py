from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Placeholder custom user model.

    A custom AUTH_USER_MODEL must exist before the first migration, so this
    is scaffolded in Phase 0. Full fields (phone_number, timezone,
    slack_user_id) are added in Phase 1 per the spec's Section 5 data model.
    """
