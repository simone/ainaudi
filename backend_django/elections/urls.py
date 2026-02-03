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
    path('', ConsultazioniListView.as_view(), name='elections-list'),
    path('active/', ConsultazioneAttivaView.as_view(), name='election-active'),
    path('<int:pk>/', ConsultazioneDetailView.as_view(), name='election-detail'),
    path('ballots/<int:pk>/', SchedaElettoraleDetailView.as_view(), name='ballot-detail'),
]
