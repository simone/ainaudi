"""
Delegations URL configuration.

Endpoints:
- GET /api/deleghe/mia-catena/ - La catena deleghe dell'utente loggato
- /api/deleghe/sub-deleghe/ - CRUD Sub-Deleghe
- /api/deleghe/designazioni/ - CRUD Designazioni RDL
- /api/deleghe/designazioni/sezioni_disponibili/ - Sezioni disponibili per designazione
- /api/deleghe/designazioni/rdl_disponibili/ - RDL approvati per mappatura
- POST /api/deleghe/designazioni/mappatura/ - Crea mappatura RDL->Sezione
- GET /api/deleghe/designazioni/bozze_da_confermare/ - Lista bozze da confermare
- POST /api/deleghe/designazioni/{id}/conferma/ - Conferma una bozza
- POST /api/deleghe/designazioni/{id}/rifiuta/ - Rifiuta una bozza
- /api/deleghe/batch/ - Generazione batch documenti (vecchio workflow)
- /api/deleghe/processi/ - Processo completo designazione (nuovo workflow template-driven)
- /api/deleghe/campagne/ - CRUD Campagne di reclutamento
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MiaCatenaView,
    SubDelegaViewSet,
    DesignazioneRDLViewSet,
    BatchGenerazioneDocumentiViewSet,
    ProcessoDesignazioneViewSet,
)
from .views_campagna import (
    CampagnaListCreateView,
    CampagnaDetailView,
    CampagnaAttivaView,
    CampagnaChiudiView,
)

router = DefaultRouter()
router.register(r'sub-deleghe', SubDelegaViewSet, basename='sub-delega')
router.register(r'designazioni', DesignazioneRDLViewSet, basename='designazione')
router.register(r'batch', BatchGenerazioneDocumentiViewSet, basename='batch')  # Vecchio endpoint (retrocompatibilità)
router.register(r'processi', ProcessoDesignazioneViewSet, basename='processo')  # Nuovo workflow template-driven

urlpatterns = [
    path('mia-catena/', MiaCatenaView.as_view(), name='mia-catena'),
    path('campagne/', CampagnaListCreateView.as_view(), name='campagna-list-create'),
    path('campagne/<int:pk>/', CampagnaDetailView.as_view(), name='campagna-detail'),
    path('campagne/<int:pk>/attiva/', CampagnaAttivaView.as_view(), name='campagna-attiva'),
    path('campagne/<int:pk>/chiudi/', CampagnaChiudiView.as_view(), name='campagna-chiudi'),
    path('', include(router.urls)),
]
