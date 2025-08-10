from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    def ready(self):  # noqa: D401
        # Import signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
