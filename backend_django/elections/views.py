"""
Views for elections API endpoints.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ConsultazioneElettorale, TipoElezione, SchedaElettorale,
    ListaElettorale, Candidato,
)
from .serializers import (
    ConsultazioneElettoraleSerializer, ConsultazioneElettoraleDetailSerializer,
    TipoElezioneSerializer, TipoElezioneDetailSerializer,
    SchedaElettoraleSerializer, SchedaElettoraleDetailSerializer,
    ListaElettoraleSerializer, ListaElettoraleListSerializer,
    CandidatoSerializer, CandidatoListSerializer,
)


class ConsultazioneElettoraleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ConsultazioneElettorale (read-only).

    GET /api/elections/consultazioni/
    GET /api/elections/consultazioni/{id}/
    GET /api/elections/consultazioni/attiva/
    """
    queryset = ConsultazioneElettorale.objects.prefetch_related('tipi_elezione').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_attiva']
    search_fields = ['nome']

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'attiva':
            return ConsultazioneElettoraleDetailSerializer
        return ConsultazioneElettoraleSerializer

    @action(detail=False, methods=['get'])
    def attiva(self, request):
        """Get the currently active electoral consultation."""
        consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
        if not consultazione:
            return Response({'detail': 'Nessuna consultazione attiva'}, status=404)
        serializer = ConsultazioneElettoraleDetailSerializer(consultazione)
        return Response(serializer.data)


class TipoElezioneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for TipoElezione (read-only).

    GET /api/elections/tipi/
    GET /api/elections/tipi/{id}/
    """
    queryset = TipoElezione.objects.select_related('consultazione', 'regione').prefetch_related('schede').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['consultazione', 'tipo', 'ambito_nazionale', 'regione']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TipoElezioneDetailSerializer
        return TipoElezioneSerializer


class SchedaElettoraleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SchedaElettorale (read-only).

    GET /api/elections/schede/
    GET /api/elections/schede/{id}/
    """
    queryset = SchedaElettorale.objects.select_related('tipo_elezione').prefetch_related('liste', 'candidati_uninominali').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['tipo_elezione', 'tipo_elezione__tipo']
    search_fields = ['nome']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SchedaElettoraleDetailSerializer
        return SchedaElettoraleSerializer


class ListaElettoraleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ListaElettorale (read-only).

    GET /api/elections/liste/
    GET /api/elections/liste/{id}/
    """
    queryset = ListaElettorale.objects.select_related('scheda', 'coalizione').prefetch_related('candidati').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['scheda', 'coalizione']
    search_fields = ['nome', 'nome_breve']

    def get_serializer_class(self):
        if self.action == 'list':
            return ListaElettoraleListSerializer
        return ListaElettoraleSerializer


class CandidatoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Candidato (read-only).

    GET /api/elections/candidati/
    GET /api/elections/candidati/{id}/
    """
    queryset = Candidato.objects.select_related('lista', 'scheda').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lista', 'scheda', 'is_sindaco', 'is_presidente']
    search_fields = ['nome', 'cognome']

    def get_serializer_class(self):
        if self.action == 'list':
            return CandidatoListSerializer
        return CandidatoSerializer
