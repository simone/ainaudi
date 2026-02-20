"""
Minimal settings for PDF generation service.

Only loads apps needed for the designation/PDF workflow:
core, territory, elections, delegations, campaign, data, documents.
No admin, no sessions, no allauth, no kpi, no incidents, no resources, no AI.
"""
from config.settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    # API
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',

    # Project apps (minimum for PDF generation)
    'core.apps.CoreConfig',
    'territory.apps.TerritoryConfig',
    'elections.apps.ElectionsConfig',
    'delegations.apps.DelegationsConfig',
    'campaign.apps.CampaignConfig',
    'data.apps.DataConfig',
    'documents.apps.DocumentsConfig',
]

# Minimal middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls_pdf'
WSGI_APPLICATION = 'config.wsgi_pdf.application'

# No templates needed (API-only)
TEMPLATES = []

# No static files
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# JWT only
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
