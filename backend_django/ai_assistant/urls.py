"""
AI Assistant URL configuration.
"""
from django.urls import path
from .views import ChatView, ChatSessionsView, KnowledgeSourcesView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='ai-chat'),
    path('sessions/', ChatSessionsView.as_view(), name='ai-sessions'),
    path('knowledge/', KnowledgeSourcesView.as_view(), name='ai-knowledge'),
]
