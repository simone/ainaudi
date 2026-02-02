"""
Views for elections API endpoints.
Only exposes endpoints needed by the frontend.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

from .models import (
    ConsultazioneElettorale, ListaElettorale, Candidato,
)


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class ConsultazioneAttivaView(APIView):
    """
    Get the currently active electoral consultation.

    GET /api/elections/consultazioni/attiva/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({})

        # Get schede for this consultation
        schede = []
        for tipo in consultazione.tipi_elezione.all():
            for scheda in tipo.schede.all():
                schede.append({
                    'id': scheda.id,
                    'nome': scheda.nome,
                    'colore': scheda.colore,
                    'tipo': tipo.tipo,
                    'testo_quesito': scheda.testo_quesito,
                    'schema_voti': scheda.schema_voti,
                })

        return Response({
            'id': consultazione.id,
            'nome': consultazione.nome,
            'data_inizio': consultazione.data_inizio,
            'data_fine': consultazione.data_fine,
            'descrizione': consultazione.descrizione,
            'schede': schede,
        })


class ElectionListsView(APIView):
    """
    Get electoral lists for the active consultation.

    GET /api/election/lists

    Returns format expected by frontend: {values: [[nome1], [nome2], ...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'values': []})

        # Get all lists for this consultation
        liste = ListaElettorale.objects.filter(
            scheda__tipo_elezione__consultazione=consultazione
        ).order_by('ordine_scheda').values_list('nome', flat=True)

        # Format expected by frontend: [[nome1], [nome2], ...]
        values = [[nome] for nome in liste]

        return Response({'values': values})


class ElectionCandidatesView(APIView):
    """
    Get candidates for the active consultation.

    GET /api/election/candidates

    Returns format expected by frontend: {values: [nome1, nome2, ...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({'values': []})

        # Get all candidates for this consultation
        candidati = Candidato.objects.filter(
            lista__scheda__tipo_elezione__consultazione=consultazione
        ).order_by('lista', 'posizione_lista')

        # Format expected by frontend: array of names
        values = [f"{c.cognome} {c.nome}" for c in candidati]

        return Response({'values': values})
