from django.apps import AppConfig


class DelegationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'delegations'
    verbose_name = 'Deleghe'

    def ready(self):
        """Import signals for automatic user provisioning."""
        from . import signals  # noqa: F401
