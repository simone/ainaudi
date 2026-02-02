"""
Elections URL configuration.
Only exposes endpoints needed by the frontend.
"""
from django.urls import path
from .views import (
    ConsultazioneAttivaView,
    ElectionListsView,
    ElectionCandidatesView,
)

urlpatterns = [
    path('consultazioni/attiva/', ConsultazioneAttivaView.as_view(), name='consultazione-attiva'),
]
