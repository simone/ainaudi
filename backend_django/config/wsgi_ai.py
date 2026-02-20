"""
WSGI config for AI Assistant service.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_ai')

application = get_wsgi_application()
