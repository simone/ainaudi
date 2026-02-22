"""
Documents URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TemplateViewSet,
    GeneratedDocumentViewSet,
    GeneratePDFView,
    RequestPDFPreviewView,
    ConfirmPDFView,
    TemplateEditorView,
    TemplatePreviewView,
    ServeMediaView,
    VisibleDelegatesView,
)

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')
router.register(r'generated', GeneratedDocumentViewSet, basename='generated-document')

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', GeneratePDFView.as_view(), name='generate-pdf'),  # Legacy
    path('preview/', RequestPDFPreviewView.as_view(), name='request-pdf-preview'),
    path('confirm/', ConfirmPDFView.as_view(), name='confirm-pdf'),
    path('templates/<int:pk>/editor/', TemplateEditorView.as_view(), name='template-editor'),
    path('templates/<int:pk>/preview/', TemplatePreviewView.as_view(), name='template-preview'),
    path('visible-delegates/', VisibleDelegatesView.as_view(), name='visible-delegates'),
    # Serve media files through API (Vite proxy workaround)
    path('media/<path:filepath>', ServeMediaView.as_view(), name='serve-media'),
]
