"""
Custom context processors for the admin interface.
"""
from django.conf import settings


def branding(request):
    """
    Add branding settings to template context.

    Usage in templates:
        {{ ADMIN_LOGO }}  - 'ainaudi' or 'm5s'
        {{ ADMIN_SITE_HEADER }}
        {{ ADMIN_SITE_TITLE }}
    """
    return {
        'ADMIN_LOGO': getattr(settings, 'ADMIN_LOGO', 'ainaudi'),
        'ADMIN_SITE_HEADER': getattr(settings, 'ADMIN_SITE_HEADER', 'AInaudi Admin'),
        'ADMIN_SITE_TITLE': getattr(settings, 'ADMIN_SITE_TITLE', 'AInaudi'),
        'ADMIN_INDEX_TITLE': getattr(settings, 'ADMIN_INDEX_TITLE', 'Gestione Sistema'),
    }
