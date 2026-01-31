"""
URL configuration for RDL Referendum project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from core.admin_views import (
    AdminMagicLinkRequestView,
    AdminMagicLinkVerifyView,
)

urlpatterns = [
    # Root redirect to admin
    path('', RedirectView.as_view(url='/admin/', permanent=False)),

    # Admin Magic Link (before admin/)
    path('admin/magic-link/', AdminMagicLinkRequestView.as_view(), name='admin_magic_link_request'),
    path('admin/magic-link/verify/', AdminMagicLinkVerifyView.as_view(), name='admin_magic_link_verify'),

    # Django Admin
    path('admin/', admin.site.urls),

    # Custom auth endpoints (Google OAuth, Magic Link) - no signup, no password login
    path('api/auth/', include('core.urls')),

    # API endpoints
    path('api/territorio/', include('territorio.urls')),
    path('api/elections/', include('elections.urls')),
    path('api/sections/', include('sections.urls')),
    path('api/delegations/', include('delegations.urls')),
    path('api/incidents/', include('incidents.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/kpi/', include('kpi.urls')),

    # AI Assistant (feature-flagged)
    path('api/ai/', include('ai_assistant.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = 'RDL 5 Stelle'
admin.site.site_title = 'RDL 5 Stelle'
admin.site.index_title = 'Gestione Referendum'
