"""
WSGI config for API service (no admin).
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_api')

application = get_wsgi_application()
