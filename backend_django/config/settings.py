"""
Django settings for RDL Referendum project.

For production deployment on Google App Engine with Cloud SQL.
"""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# CSRF settings
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third-party apps
    'rest_framework',
    # 'rest_framework.authtoken',  # Removed: using JWT, not token auth
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'dj_rest_auth',
    # 'dj_rest_auth.registration',  # Disabled - we use custom Google OAuth and Magic Link

    # Project apps
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Default SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL for production (Cloud SQL)
if os.environ.get('DATABASE_URL'):
    # Parse DATABASE_URL format: postgres://user:password@host:port/dbname
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
elif os.environ.get('CLOUD_SQL_CONNECTION_NAME'):
    # Google Cloud SQL via Unix socket
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'rdl_referendum'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME')}",
        'PORT': '5432',
    }
elif os.environ.get('DB_HOST'):
    # Direct PostgreSQL connection
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'rdl_referendum'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }


# =============================================================================
# AUTHENTICATION
# =============================================================================

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Django-allauth configuration
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Our User model has no username field
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_UNIQUE_EMAIL = True



# =============================================================================
# REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 200,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/minute',
        'user': '120/minute',
    },
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
}

# dj-rest-auth settings
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'rdl-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'rdl-refresh',
    'JWT_AUTH_HTTPONLY': True,
    'SESSION_LOGIN': False,
    'TOKEN_MODEL': None,  # Disable token auth, using JWT only
}


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',')

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Google Cloud Storage for production (GAE)
# Install: pip install django-storages[google]
USE_GCS = os.environ.get('USE_GCS', 'False').lower() == 'true'
if USE_GCS:
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME', 'rdl-media-bucket')
    GS_PROJECT_ID = os.environ.get('GS_PROJECT_ID', '')
    GS_DEFAULT_ACL = 'publicRead'  # Files publicly accessible
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'


# =============================================================================
# BRANDING SETTINGS
# =============================================================================

# Logo to use in admin panel: 'ainaudi' or 'm5s'
# Set via environment variable ADMIN_LOGO
ADMIN_LOGO = os.environ.get('ADMIN_LOGO', 'ainaudi')  # 'ainaudi' or 'm5s'

# App name displayed in admin
ADMIN_SITE_HEADER = os.environ.get('ADMIN_SITE_HEADER', 'AInaudi Admin')
ADMIN_SITE_TITLE = os.environ.get('ADMIN_SITE_TITLE', 'AInaudi')
ADMIN_INDEX_TITLE = os.environ.get('ADMIN_INDEX_TITLE', 'Gestione Sistema')


# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'delegations.signals': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'data.signals': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# =============================================================================
# FEATURE FLAGS
# =============================================================================

FEATURE_FLAGS = {
    'MAGIC_LINK': os.environ.get('FEATURE_MAGIC_LINK', 'true').lower() == 'true',
    'M5S_SSO': os.environ.get('FEATURE_M5S_SSO', 'false').lower() == 'true',
    'INCIDENT_REPORTS': os.environ.get('FEATURE_INCIDENT_REPORTS', 'true').lower() == 'true',
    'SECTION_IMPORT': os.environ.get('FEATURE_SECTION_IMPORT', 'true').lower() == 'true',
    'TEMPLATES_ENGINE': os.environ.get('FEATURE_TEMPLATES_ENGINE', 'true').lower() == 'true',
    'AI_ASSISTANT': os.environ.get('FEATURE_AI_ASSISTANT', 'false').lower() == 'true',
}


# =============================================================================
# GOOGLE CLOUD STORAGE (for PDF files)
# =============================================================================

GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'rdl-referendum-documents')
GCS_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'rdl-europee-2024')


# =============================================================================
# EMAIL CONFIGURATION (for Magic Link)
# =============================================================================

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@m5s.it')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')


# =============================================================================
# MAGIC LINK SETTINGS
# =============================================================================

MAGIC_LINK_TOKEN_EXPIRY = int(os.environ.get('MAGIC_LINK_TOKEN_EXPIRY', 3600))  # 1 hour


# =============================================================================
# REDIS EVENT BUS
# =============================================================================

# Redis Configuration for Event-Driven PDF Generation
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
REDIS_PDF_EVENT_CHANNEL = 'pdf_events'

# PDF Preview Expiry (24 hours default)
PDF_PREVIEW_EXPIRY_SECONDS = int(os.environ.get('PDF_PREVIEW_EXPIRY_SECONDS', 86400))
