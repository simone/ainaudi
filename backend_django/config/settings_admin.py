"""
Settings for Admin service.

Full Django with admin interface, sessions, static files.
All apps loaded because admin registers models from every app.
Scale-to-zero: only wakes up when accessing /admin/.
"""
from config.settings import *  # noqa: F401,F403

# Full INSTALLED_APPS with admin and all dependencies
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party (allauth for admin cleanup compatibility)
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # All project apps (admin registers models from all)
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
    'ai_assistant.apps.AiAssistantConfig',
]

# Full middleware for admin (sessions, CSRF, messages)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls_admin'
WSGI_APPLICATION = 'config.wsgi_admin.application'
