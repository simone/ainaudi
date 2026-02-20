"""
URL configuration for Admin service.

Only exposes /admin/ and admin magic link.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from core.admin_views import (
    AdminMagicLinkRequestView,
    AdminMagicLinkVerifyView,
)

urlpatterns = [
    # Admin Magic Link (before admin/)
    path('admin/magic-link/', AdminMagicLinkRequestView.as_view(), name='admin_magic_link_request'),
    path('admin/magic-link/verify/', AdminMagicLinkVerifyView.as_view(), name='admin_magic_link_verify'),

    # Django Admin
    path('admin/', admin.site.urls),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = 'AInaudi'
admin.site.site_title = 'AInaudi'
admin.site.index_title = 'AInaudi - Gestione Elettorale'

# Cleanup admin: remove unused models
from config import admin_cleanup  # noqa: F401, E402
