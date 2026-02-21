"""
URL configuration for API service (no admin, no AI).

All API endpoints except /admin/ and /api/ai/.
"""
from django.urls import path, include
from django.conf import settings

from core.views import PermissionsView
from data.views import (
    RdlEmailsView,
    RdlSectionsView,
    RdlAssignView,
    RdlUnassignView,
)
from data.urls import rdl_registration_urlpatterns, mappatura_urlpatterns, scrutinio_urlpatterns
from campaign.urls import email_template_urlpatterns
from elections.views import ElectionListsView, ElectionCandidatesView
from delegations.views_campagna import CampagnaPublicView, CampagnaRegistraView

urlpatterns = [
    # Auth (Magic Link + JWT)
    path('api/auth/', include('core.urls')),

    # Permissions
    path('api/permissions', PermissionsView.as_view(), name='permissions'),

    # RDL assignment
    path('api/rdl/emails', RdlEmailsView.as_view(), name='rdl-emails'),
    path('api/rdl/sections', RdlSectionsView.as_view(), name='rdl-sections'),
    path('api/rdl/assign', RdlAssignView.as_view(), name='rdl-assign'),
    path('api/rdl/unassign', RdlUnassignView.as_view(), name='rdl-unassign'),
    path('api/rdl/', include(rdl_registration_urlpatterns)),

    # Email templates and mass email (campaign)
    path('api/rdl/', include(email_template_urlpatterns)),

    # Mapping
    path('api/mapping/', include(mappatura_urlpatterns)),
    path('api/mappatura/', include(mappatura_urlpatterns)),

    # Scrutinio
    path('api/scrutinio/', include(scrutinio_urlpatterns)),

    # Elections
    path('api/election/lists', ElectionListsView.as_view(), name='election-lists'),
    path('api/election/candidates', ElectionCandidatesView.as_view(), name='election-candidates'),
    path('api/elections/', include('elections.urls')),

    # Other API endpoints
    path('api/sections/', include('data.urls')),
    path('api/kpi/', include('kpi.urls')),
    path('api/resources/', include('resources.urls')),
    path('api/risorse/', include('resources.urls')),
    path('api/delegations/', include('delegations.urls')),
    path('api/deleghe/', include('delegations.urls')),
    path('api/territory/', include('territory.urls')),
    path('api/documents/', include('documents.urls')),

    # Public campaign (no auth)
    path('api/campagna/<slug:slug>/', CampagnaPublicView.as_view(), name='campagna-public'),
    path('api/campagna/<slug:slug>/registra/', CampagnaRegistraView.as_view(), name='campagna-registra'),
]
