from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'resources'
    verbose_name = 'Risorse (Documenti e FAQ)'

    def ready(self):
        import resources.signals  # Register signals for auto-ingestion
