"""
Sections URL configuration.
Only exposes endpoints needed by the frontend.
"""
from django.urls import path
from .views import (
    SectionsStatsView,
    SectionsOwnView,
    SectionsAssignedView,
    SectionsSaveView,
    SectionsUploadView,
    SezioniSearchPublicView,
    RdlRegistrationSelfView,
    RdlRegistrationListView,
    RdlRegistrationApproveView,
    RdlRegistrationEditView,
    RdlRegistrationImportView,
    ComuniSearchView,
    RdlRegistrationStatusView,
    # Mappatura views
    MappaturaDebugView,
    MappaturaSezioniView,
    MappaturaRdlView,
    MappaturaAssegnaView,
    MappaturaAssegnaBulkView,
)

urlpatterns = [
    path('stats', SectionsStatsView.as_view(), name='sections-stats'),
    path('own', SectionsOwnView.as_view(), name='sections-own'),
    path('assigned', SectionsAssignedView.as_view(), name='sections-assigned'),
    path('upload', SectionsUploadView.as_view(), name='sections-upload'),
    path('search-public/', SezioniSearchPublicView.as_view(), name='sections-search-public'),
    path('comuni/search', ComuniSearchView.as_view(), name='sections-comuni-search'),
    path('', SectionsSaveView.as_view(), name='sections-save'),
]

# RDL Registration URLs (mounted at /api/rdl/ in main urls.py)
rdl_registration_urlpatterns = [
    path('register', RdlRegistrationSelfView.as_view(), name='rdl-register'),
    path('register/status', RdlRegistrationStatusView.as_view(), name='rdl-register-status'),
    path('comuni/search', ComuniSearchView.as_view(), name='comuni-search'),
    path('registrations', RdlRegistrationListView.as_view(), name='rdl-registrations-list'),
    path('registrations/import', RdlRegistrationImportView.as_view(), name='rdl-registrations-import'),
    path('registrations/<int:pk>', RdlRegistrationEditView.as_view(), name='rdl-registrations-edit'),
    path('registrations/<int:pk>/<str:action>', RdlRegistrationApproveView.as_view(), name='rdl-registrations-action'),
]

# Mappatura URLs (mounted at /api/mappatura/ in main urls.py)
mappatura_urlpatterns = [
    path('debug/', MappaturaDebugView.as_view(), name='mappatura-debug'),
    path('sezioni/', MappaturaSezioniView.as_view(), name='mappatura-sezioni'),
    path('rdl/', MappaturaRdlView.as_view(), name='mappatura-rdl'),
    path('assegna/', MappaturaAssegnaView.as_view(), name='mappatura-assegna'),
    path('assegna/<int:assignment_id>/', MappaturaAssegnaView.as_view(), name='mappatura-assegna-detail'),
    path('assegna-bulk/', MappaturaAssegnaBulkView.as_view(), name='mappatura-assegna-bulk'),
]
