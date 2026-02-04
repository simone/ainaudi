"""
URL configuration for territorio app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegioneViewSet,
    ProvinciaViewSet,
    ComuneViewSet,
    MunicipioViewSet,
    SezioneElettoraleViewSet,
)

router = DefaultRouter()
router.register(r'regioni', RegioneViewSet, basename='regione')
router.register(r'province', ProvinciaViewSet, basename='provincia')
router.register(r'comuni', ComuneViewSet, basename='comune')
router.register(r'municipi', MunicipioViewSet, basename='municipio')
router.register(r'sezioni', SezioneElettoraleViewSet, basename='sezione')

urlpatterns = [
    path('', include(router.urls)),
]
