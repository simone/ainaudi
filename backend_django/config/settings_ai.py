"""
Minimal Django settings for AI Assistant service.

Loads only core + territory + ai_assistant apps.
No admin, no sessions, no allauth, no other project apps.
"""
from config.settings import *  # noqa: F401,F403

# Override: minimal INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    # API
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Project apps (minimum for AI)
    'core.apps.CoreConfig',
    'territory.apps.TerritoryConfig',
    'ai_assistant.apps.AiAssistantConfig',
]

# Override: minimal middleware (no sessions, no admin, no allauth)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]

# Override: AI-only URL routing
ROOT_URLCONF = 'config.urls_ai'
WSGI_APPLICATION = 'config.wsgi_ai.application'

# No templates needed (API-only)
TEMPLATES = []

# No static files (API-only)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Override DRF: JWT only, no session auth (no sessions middleware)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
