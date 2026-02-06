"""
Views for KPI dashboard endpoints.
Only exposes endpoints needed by the frontend.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.permissions import CanViewKPI
from elections.models import ConsultazioneElettorale
from territory.models import SezioneElettorale
from data.models import SectionAssignment, DatiSezione


def get_consultazione_attiva():
    """Get the currently active consultation."""
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class KPIDatiView(APIView):
    """
    Aggregated KPI data.

    GET /api/kpi/dati

    Returns aggregated statistics for the active consultation.

    Permission: can_view_kpi (Delegato, SubDelegato, KPI_VIEWER)
    """
    permission_classes = [permissions.IsAuthenticated, CanViewKPI]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response({
                'total_sezioni': 0,
                'sezioni_assegnate': 0,
                'sezioni_complete': 0,
                'totale_elettori': 0,
                'totale_votanti': 0,
                'affluenza_percent': 0,
            })

        # Sections stats
        total_sections = SezioneElettorale.objects.filter(is_attiva=True).count()
        assigned_sections = SectionAssignment.objects.filter(
            consultazione=consultazione,
            is_active=True
        ).values('sezione').distinct().count()

        # Data collection stats
        dati_sezioni = DatiSezione.objects.filter(consultazione=consultazione)
        sections_complete = dati_sezioni.filter(is_complete=True).count()

        # Turnout aggregation
        aggregated = dati_sezioni.filter(is_complete=True).aggregate(
            total_elettori_m=Coalesce(Sum('elettori_maschi'), 0),
            total_elettori_f=Coalesce(Sum('elettori_femmine'), 0),
            total_votanti_m=Coalesce(Sum('votanti_maschi'), 0),
            total_votanti_f=Coalesce(Sum('votanti_femmine'), 0),
        )

        totale_elettori = aggregated['total_elettori_m'] + aggregated['total_elettori_f']
        totale_votanti = aggregated['total_votanti_m'] + aggregated['total_votanti_f']
        affluenza = round((totale_votanti / totale_elettori * 100) if totale_elettori else 0, 2)

        return Response({
            'total_sezioni': total_sections,
            'sezioni_assegnate': assigned_sections,
            'sezioni_complete': sections_complete,
            'totale_elettori': totale_elettori,
            'totale_votanti': totale_votanti,
            'affluenza_percent': affluenza,
            'copertura_percent': round((assigned_sections / total_sections * 100) if total_sections else 0, 1),
            'completamento_percent': round((sections_complete / total_sections * 100) if total_sections else 0, 1),
        })


class KPISezioniView(APIView):
    """
    Section-by-section data for KPI view.

    GET /api/kpi/sezioni

    Returns list of all sections with their status and data.

    Permission: can_view_kpi (Delegato, SubDelegato, KPI_VIEWER)
    """
    permission_classes = [permissions.IsAuthenticated, CanViewKPI]

    def get(self, request):
        consultazione = get_consultazione_attiva()
        if not consultazione:
            return Response([])

        # Get all sections with their data
        sezioni = SezioneElettorale.objects.filter(
            is_attiva=True
        ).select_related('comune', 'comune__provincia').order_by('comune__nome', 'numero')

        result = []
        for sezione in sezioni:
            # Get assignment
            assignment = SectionAssignment.objects.filter(
                sezione=sezione,
                consultazione=consultazione,
                is_active=True
            ).select_related('rdl_registration').first()

            # Get dati
            dati = DatiSezione.objects.filter(
                sezione=sezione,
                consultazione=consultazione
            ).first()

            result.append({
                'comune': sezione.comune.nome,
                'sezione': sezione.numero,
                'municipio': f"Municipio {sezione.municipio.numero}" if sezione.municipio else None,
                'email': assignment.rdl_registration.email if assignment and assignment.rdl_registration else None,
                'is_complete': dati.is_complete if dati else False,
                'elettori_maschi': dati.elettori_maschi if dati else None,
                'elettori_femmine': dati.elettori_femmine if dati else None,
                'votanti_maschi': dati.votanti_maschi if dati else None,
                'votanti_femmine': dati.votanti_femmine if dati else None,
            })

        return Response(result)
