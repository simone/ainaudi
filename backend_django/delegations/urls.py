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
- /api/deleghe/batch/ - Generazione batch documenti
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MiaCatenaView,
    SubDelegaViewSet,
    DesignazioneRDLViewSet,
    BatchGenerazioneDocumentiViewSet,
)

router = DefaultRouter()
router.register(r'sub-deleghe', SubDelegaViewSet, basename='sub-delega')
router.register(r'designazioni', DesignazioneRDLViewSet, basename='designazione')
router.register(r'batch', BatchGenerazioneDocumentiViewSet, basename='batch')

urlpatterns = [
    path('mia-catena/', MiaCatenaView.as_view(), name='mia-catena'),
    path('', include(router.urls)),
]
