"""
Views for territorio API endpoints.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django_filters.rest_framework import DjangoFilterBackend

from .models import Regione, Provincia, Comune, SezioneElettorale
from .serializers import (
    RegioneSerializer,
    ProvinciaSerializer, ProvinciaListSerializer,
    ComuneSerializer, ComuneListSerializer,
    SezioneElettoraleSerializer, SezioneElettoraleListSerializer,
)


class RegioneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Regione (read-only).

    GET /api/territorio/regioni/
    GET /api/territorio/regioni/{id}/
    """
    queryset = Regione.objects.all()
    serializer_class = RegioneSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['statuto_speciale']
    search_fields = ['nome', 'codice_istat']


class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Provincia (read-only).

    GET /api/territorio/province/
    GET /api/territorio/province/{id}/
    """
    queryset = Provincia.objects.select_related('regione').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['regione', 'is_citta_metropolitana']
    search_fields = ['nome', 'sigla', 'codice_istat']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProvinciaListSerializer
        return ProvinciaSerializer


class ComuneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Comune (read-only).

    GET /api/territorio/comuni/
    GET /api/territorio/comuni/{id}/      (accepts numeric ID or comune name)
    GET /api/territorio/comuni/{id}/sezioni/
    """
    queryset = Comune.objects.select_related('provincia', 'provincia__regione').prefetch_related('municipi').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['provincia', 'provincia__regione']
    search_fields = ['nome', 'codice_istat', 'codice_catastale']
    # Allow both numeric IDs and names in URL
    lookup_value_regex = '[^/]+'

    def get_serializer_class(self):
        if self.action == 'list':
            return ComuneListSerializer
        return ComuneSerializer

    def get_object(self):
        """Override to accept both numeric ID and comune name."""
        lookup_value = self.kwargs.get(self.lookup_field)

        # Try numeric ID first
        try:
            pk = int(lookup_value)
            return self.queryset.get(pk=pk)
        except (ValueError, TypeError):
            pass
        except Comune.DoesNotExist:
            raise NotFound(f'Comune con ID {lookup_value} non trovato')

        # Try by name (case-insensitive)
        try:
            return self.queryset.get(nome__iexact=lookup_value)
        except Comune.DoesNotExist:
            raise NotFound(f'Comune "{lookup_value}" non trovato')

    @action(detail=True, methods=['get'])
    def sezioni(self, request, pk=None):
        """Get all electoral sections for a municipality."""
        comune = self.get_object()
        sezioni = comune.sezioni.filter(is_attiva=True).order_by('numero')
        serializer = SezioneElettoraleListSerializer(sezioni, many=True)
        return Response(serializer.data)


class SezioneElettoraleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SezioneElettorale (read-only).

    GET /api/territorio/sezioni/
    GET /api/territorio/sezioni/{id}/
    """
    queryset = SezioneElettorale.objects.select_related('comune', 'comune__provincia', 'municipio').all()
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['comune', 'municipio', 'is_attiva']
    search_fields = ['numero', 'comune__nome', 'indirizzo', 'denominazione']

    def get_serializer_class(self):
        if self.action == 'list':
            return SezioneElettoraleListSerializer
        return SezioneElettoraleSerializer
