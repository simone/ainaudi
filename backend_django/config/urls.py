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
from core.views import PermissionsView
from data.views import (
    RdlEmailsView,
    RdlSectionsView,
    RdlAssignView,
    RdlUnassignView,
)
from data.urls import rdl_registration_urlpatterns, mappatura_urlpatterns
from elections.views import ElectionListsView, ElectionCandidatesView
from delegations.views_campagna import CampagnaPublicView, CampagnaRegistraView

urlpatterns = [
    # Root redirect to admin
    path('', RedirectView.as_view(url='/admin/', permanent=False)),

    # Admin Magic Link (before admin/)
    path('admin/magic-link/', AdminMagicLinkRequestView.as_view(), name='admin_magic_link_request'),
    path('admin/magic-link/verify/', AdminMagicLinkVerifyView.as_view(), name='admin_magic_link_verify'),

    # Django Admin
    path('admin/', admin.site.urls),

    # Custom auth endpoints (Magic Link) - no signup, no password login
    path('api/auth/', include('core.urls')),

    # Permissions endpoint
    path('api/permissions', PermissionsView.as_view(), name='permissions'),

    # RDL assignment endpoints
    path('api/rdl/emails', RdlEmailsView.as_view(), name='rdl-emails'),
    path('api/rdl/sections', RdlSectionsView.as_view(), name='rdl-sections'),
    path('api/rdl/assign', RdlAssignView.as_view(), name='rdl-assign'),
    path('api/rdl/unassign', RdlUnassignView.as_view(), name='rdl-unassign'),

    # RDL registration endpoints
    path('api/rdl/', include(rdl_registration_urlpatterns)),

    # Mapping endpoints (operational RDL-to-station assignment)
    path('api/mapping/', include(mappatura_urlpatterns)),

    # Election endpoints (singular 'election' for frontend compatibility)
    path('api/election/lists', ElectionListsView.as_view(), name='election-lists'),
    path('api/election/candidates', ElectionCandidatesView.as_view(), name='election-candidates'),

    # API endpoints used by frontend
    path('api/elections/', include('elections.urls')),
    path('api/sections/', include('data.urls')),
    path('api/kpi/', include('kpi.urls')),
    path('api/resources/', include('resources.urls')),
    path('api/delegations/', include('delegations.urls')),
    path('api/territory/', include('territory.urls')),

    # Public campaign endpoints (no auth required)
    path('api/campaigns/<slug:slug>/', CampagnaPublicView.as_view(), name='campaign-public'),
    path('api/campaigns/<slug:slug>/register/', CampagnaRegistraView.as_view(), name='campaign-register'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = 'RDL 5 Stelle'
admin.site.site_title = 'RDL 5 Stelle'
admin.site.index_title = 'RDL 5 Stelle'

# Cleanup admin: remove unused models (Sites, Social accounts, etc.)
# Must be imported AFTER admin.site.urls is included
from config import admin_cleanup  # noqa: F401, E402
