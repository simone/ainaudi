"""
Incidents URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IncidentReportViewSet,
    IncidentCommentViewSet,
    IncidentAttachmentViewSet,
    SuggestIncidentFromChatView,
)

router = DefaultRouter()
router.register(r'reports', IncidentReportViewSet, basename='incident')
router.register(r'comments', IncidentCommentViewSet, basename='incident-comment')
router.register(r'attachments', IncidentAttachmentViewSet, basename='incident-attachment')

urlpatterns = [
    path('', include(router.urls)),
    path('suggest-from-chat/', SuggestIncidentFromChatView.as_view(), name='suggest-incident-from-chat'),
]
