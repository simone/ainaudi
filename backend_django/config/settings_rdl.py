"""
Settings for RDL service (scrutinio + risorse).

High-traffic service on election day. Scales horizontally.
Only loads apps needed for vote data entry and resources.
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

    # Project apps (minimum for scrutinio + risorse)
    'core.apps.CoreConfig',
    'territory.apps.TerritoryConfig',
    'elections.apps.ElectionsConfig',
    'data.apps.DataConfig',
    'delegations.apps.DelegationsConfig',  # data.views imports delegations.models
    'campaign.apps.CampaignConfig',
    'documents.apps.DocumentsConfig',  # delegations.models imports documents.models
    'resources.apps.ResourcesConfig',
]

# Minimal middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls_rdl'
WSGI_APPLICATION = 'config.wsgi_rdl.application'

# No templates needed
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
