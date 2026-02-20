"""
URL configuration for AI Assistant service.

Only exposes /api/ai/* endpoints.
"""
from django.urls import path, include

urlpatterns = [
    path('api/ai/', include('ai_assistant.urls')),
]
