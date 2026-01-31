"""
Elections URL configuration.
Territory endpoints are in territorio/urls.py.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsultazioneElettoraleViewSet,
    TipoElezioneViewSet,
    SchedaElettoraleViewSet,
    ListaElettoraleViewSet,
    CandidatoViewSet,
)

router = DefaultRouter()
router.register(r'consultazioni', ConsultazioneElettoraleViewSet, basename='consultazione')
router.register(r'tipi', TipoElezioneViewSet, basename='tipo-elezione')
router.register(r'schede', SchedaElettoraleViewSet, basename='scheda')
router.register(r'liste', ListaElettoraleViewSet, basename='lista')
router.register(r'candidati', CandidatoViewSet, basename='candidato')

urlpatterns = [
    path('', include(router.urls)),
]
