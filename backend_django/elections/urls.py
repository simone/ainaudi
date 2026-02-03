"""
Elections URL configuration.
Only exposes endpoints needed by the frontend.
"""
from django.urls import path
from .views import (
    ConsultazioniListView,
    ConsultazioneAttivaView,
    ConsultazioneDetailView,
    SchedaElettoraleDetailView,
    ElectionListsView,
    ElectionCandidatesView,
)

urlpatterns = [
    path('consultazioni/', ConsultazioniListView.as_view(), name='consultazioni-list'),
    path('consultazioni/attiva/', ConsultazioneAttivaView.as_view(), name='consultazione-attiva'),
    path('consultazioni/<int:pk>/', ConsultazioneDetailView.as_view(), name='consultazione-detail'),
    path('schede/<int:pk>/', SchedaElettoraleDetailView.as_view(), name='scheda-detail'),
]
