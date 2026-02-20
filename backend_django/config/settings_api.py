"""
Settings for API service (lightweight, no admin).

All project apps loaded for API endpoints, but no admin framework,
no sessions, no allauth, no staticfiles serving.
"""
from config.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    # Third-party API
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',

    # All project apps (API endpoints)
    'core.apps.CoreConfig',
    'territory.apps.TerritoryConfig',
    'elections.apps.ElectionsConfig',
    'data.apps.DataConfig',
    'delegations.apps.DelegationsConfig',
    'campaign.apps.CampaignConfig',
    'incidents.apps.IncidentsConfig',
    'documents.apps.DocumentsConfig',
    'resources.apps.ResourcesConfig',
    'kpi.apps.KpiConfig',
]

# No sessions, no admin, no allauth
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls_api'
WSGI_APPLICATION = 'config.wsgi_api.application'

# No templates needed (API-only, DRF browsable API disabled in prod)
TEMPLATES = []

# No static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# JWT only, no session auth
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
