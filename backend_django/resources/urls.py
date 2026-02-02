"""
URL configuration for Resources API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RisorseView, DocumentoViewSet, FAQViewSet, PDFProxyView

router = DefaultRouter()
router.register(r'documenti', DocumentoViewSet, basename='documento')
router.register(r'faqs', FAQViewSet, basename='faq')

urlpatterns = [
    path('', RisorseView.as_view(), name='risorse-list'),
    path('pdf-proxy/', PDFProxyView.as_view(), name='pdf-proxy'),
    path('', include(router.urls)),
]
