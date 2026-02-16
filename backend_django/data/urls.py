"""
Sections URL configuration.
Only exposes endpoints needed by the frontend.
"""
from django.urls import path
from .views import (
    SectionsStatsView,
    SectionsListView,
    SectionsUpdateView,
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
    RdlRegistrationRetryView,
    ComuniSearchView,
    RdlRegistrationStatusView,
    # Mappatura views
    MappaturaDebugView,
    MappaturaSezioniView,
    MappaturaRdlView,
    MappaturaAssegnaView,
    MappaturaAssegnaBulkView,
    # Scrutinio views
    ScrutinioInfoView,
    ScrutinioSezioniView,
    ScrutinioSaveView,
)
# Import optimized scrutinio views
from .views_scrutinio_optimized import (
    ScrutinioMieiSeggiLightView,
    ScrutinioSezioneDetailView,
    ScrutinioSezioneSaveView,
)
# Import aggregated scrutinio view
from .views_scrutinio_aggregato import ScrutinioAggregatoView
# Import mappatura gerarchica view
from .views_mappatura_gerarchica import MappaturaGerarchicaView
# Import mappatura analizza preferenze view
from .views_analizza_preferenze import MappaturaAnalizzaPreferenzeView
# Import mappatura report XLSX view
from .views_report_xlsx import MappaturaReportXlsxView

urlpatterns = [
    path('stats', SectionsStatsView.as_view(), name='sections-stats'),
    path('list/', SectionsListView.as_view(), name='sections-list'),
    path('<int:pk>/', SectionsUpdateView.as_view(), name='sections-update'),
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
    path('registrations/retry', RdlRegistrationRetryView.as_view(), name='rdl-registrations-retry'),
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
    path('analizza-preferenze/', MappaturaAnalizzaPreferenzeView.as_view(), name='mappatura-analizza-preferenze'),
    # Hierarchical navigation
    path('gerarchica/', MappaturaGerarchicaView.as_view(), name='mappatura-gerarchica'),
    # XLSX report
    path('report-xlsx/', MappaturaReportXlsxView.as_view(), name='mappatura-report-xlsx'),
]

# Scrutinio URLs (mounted at /api/scrutinio/ in main urls.py)
scrutinio_urlpatterns = [
    path('info', ScrutinioInfoView.as_view(), name='scrutinio-info'),
    path('sezioni', ScrutinioSezioniView.as_view(), name='scrutinio-sezioni'),
    path('save', ScrutinioSaveView.as_view(), name='scrutinio-save'),
    # Optimized endpoints with preload pattern
    path('miei-seggi-light', ScrutinioMieiSeggiLightView.as_view(), name='scrutinio-miei-seggi-light'),
    path('sezioni/<int:sezione_id>', ScrutinioSezioneDetailView.as_view(), name='scrutinio-sezione-detail'),
    path('sezioni/<int:sezione_id>/save', ScrutinioSezioneSaveView.as_view(), name='scrutinio-sezione-save'),
    # Aggregated view for delegati/subdelegati
    path('aggregato', ScrutinioAggregatoView.as_view(), name='scrutinio-aggregato'),
]
