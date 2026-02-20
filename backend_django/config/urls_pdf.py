"""
URL configuration for PDF generation service.

Only exposes /api/deleghe/processi/* (routed via dispatch.yaml).
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delegations.views_processo import ProcessoDesignazioneViewSet

router = DefaultRouter()
router.register(r'processi', ProcessoDesignazioneViewSet, basename='processo')

urlpatterns = [
    path('api/deleghe/', include(router.urls)),
]
