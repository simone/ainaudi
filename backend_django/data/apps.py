from django.apps import AppConfig


class DataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data'
    verbose_name = 'Raccolta Dati'

    def ready(self):
        """Import signals for RDL registration provisioning."""
        from . import signals  # noqa: F401
