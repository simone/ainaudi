"""
Documents URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet, GeneratedDocumentViewSet, GeneratePDFView

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'generated', GeneratedDocumentViewSet, basename='generated-document')

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', GeneratePDFView.as_view(), name='generate-pdf'),
]
