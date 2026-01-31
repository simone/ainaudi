"""
Delegations URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DelegationRelationshipViewSet,
    FreezeBatchViewSet,
    ProxyDelegationDocumentViewSet,
)

router = DefaultRouter()
router.register(r'relationships', DelegationRelationshipViewSet, basename='delegation')
router.register(r'batches', FreezeBatchViewSet, basename='freeze-batch')
router.register(r'documents', ProxyDelegationDocumentViewSet, basename='delegation-document')

urlpatterns = [
    path('', include(router.urls)),
]
