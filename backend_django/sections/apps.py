from django.apps import AppConfig


class SectionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sections'
    verbose_name = 'Raccolta Dati'

    def ready(self):
        """Import signals for RDL registration provisioning."""
        from . import signals  # noqa: F401
