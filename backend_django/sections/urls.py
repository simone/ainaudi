"""
Sections URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SectionAssignmentViewSet,
    DatiSezioneViewSet,
    DatiSchedaViewSet,
    SectionDataHistoryViewSet,
)

router = DefaultRouter()
router.register(r'assignments', SectionAssignmentViewSet, basename='assignment')
router.register(r'dati', DatiSezioneViewSet, basename='dati-sezione')
router.register(r'schede', DatiSchedaViewSet, basename='dati-scheda')
router.register(r'history', SectionDataHistoryViewSet, basename='section-history')

urlpatterns = [
    path('', include(router.urls)),
]
