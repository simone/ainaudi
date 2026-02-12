"""
AI Assistant URL configuration.
"""
from django.urls import path
from .views import ChatView, ChatBranchView, ChatSessionsView, KnowledgeSourcesView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='ai-chat'),
    path('chat/branch/', ChatBranchView.as_view(), name='ai-chat-branch'),
    path('sessions/', ChatSessionsView.as_view(), name='ai-sessions'),
    path('knowledge/', KnowledgeSourcesView.as_view(), name='ai-knowledge'),
]
