"""
WSGI config for RDL service (scrutinio + risorse).
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_rdl')

application = get_wsgi_application()
