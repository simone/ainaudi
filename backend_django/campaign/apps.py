from django.apps import AppConfig


class CampaignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'campaign'
    verbose_name = 'Campagne e Registrazioni'

    def ready(self):
        import campaign.signals  # noqa: F401
