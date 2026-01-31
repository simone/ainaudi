"""
Views for KPI dashboard endpoints.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import Coalesce

from elections.models import ConsultazioneElettorale
from territorio.models import SezioneElettorale
from sections.models import SectionAssignment, DatiSezione, DatiScheda
from incidents.models import IncidentReport


class KPIDashboardView(APIView):
    """
    Main KPI dashboard with aggregated metrics.

    GET /api/kpi/dashboard/?consultazione={id}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione')
        if not consultazione_id:
            # Get active consultation
            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return Response({'error': 'No active consultation'}, status=404)
            consultazione_id = consultazione.id

        # Sections stats
        total_sections = SezioneElettorale.objects.filter(is_attiva=True).count()
        assigned_sections = SectionAssignment.objects.filter(
            consultazione_id=consultazione_id,
            is_active=True
        ).values('sezione').distinct().count()

        # Data collection stats
        dati_sezioni = DatiSezione.objects.filter(consultazione_id=consultazione_id)
        sections_with_data = dati_sezioni.filter(is_complete=True).count()
        sections_verified = dati_sezioni.filter(is_verified=True).count()

        # Incidents stats
        incidents = IncidentReport.objects.filter(consultazione_id=consultazione_id)
        incidents_open = incidents.filter(status=IncidentReport.Status.OPEN).count()
        incidents_critical = incidents.filter(severity=IncidentReport.Severity.CRITICAL).count()

        return Response({
            'sections': {
                'total': total_sections,
                'assigned': assigned_sections,
                'with_data': sections_with_data,
                'verified': sections_verified,
                'coverage_percent': round((assigned_sections / total_sections * 100) if total_sections else 0, 1),
                'completion_percent': round((sections_with_data / total_sections * 100) if total_sections else 0, 1),
            },
            'incidents': {
                'total': incidents.count(),
                'open': incidents_open,
                'critical': incidents_critical,
            },
        })


class KPITurnoutView(APIView):
    """
    Turnout statistics.

    GET /api/kpi/turnout/?consultazione={id}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione')
        if not consultazione_id:
            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return Response({'error': 'No active consultation'}, status=404)
            consultazione_id = consultazione.id

        dati = DatiSezione.objects.filter(
            consultazione_id=consultazione_id,
            is_complete=True
        ).aggregate(
            total_elettori_m=Coalesce(Sum('elettori_maschi'), 0),
            total_elettori_f=Coalesce(Sum('elettori_femmine'), 0),
            total_votanti_m=Coalesce(Sum('votanti_maschi'), 0),
            total_votanti_f=Coalesce(Sum('votanti_femmine'), 0),
        )

        totale_elettori = dati['total_elettori_m'] + dati['total_elettori_f']
        totale_votanti = dati['total_votanti_m'] + dati['total_votanti_f']

        return Response({
            'elettori': {
                'maschi': dati['total_elettori_m'],
                'femmine': dati['total_elettori_f'],
                'totale': totale_elettori,
            },
            'votanti': {
                'maschi': dati['total_votanti_m'],
                'femmine': dati['total_votanti_f'],
                'totale': totale_votanti,
            },
            'affluenza_percent': round((totale_votanti / totale_elettori * 100) if totale_elettori else 0, 2),
        })


class KPISectionStatusView(APIView):
    """
    Section-by-section status breakdown.

    GET /api/kpi/sections/?consultazione={id}&comune={id}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione')
        comune_id = request.query_params.get('comune')

        if not consultazione_id:
            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return Response({'error': 'No active consultation'}, status=404)
            consultazione_id = consultazione.id

        # Get sections with their status
        sezioni = SezioneElettorale.objects.filter(is_attiva=True)
        if comune_id:
            sezioni = sezioni.filter(comune_id=comune_id)

        sezioni = sezioni.select_related('comune').prefetch_related(
            'assignments', 'dati'
        )

        result = []
        for sezione in sezioni[:100]:  # Limit for performance
            assignment = sezione.assignments.filter(
                consultazione_id=consultazione_id,
                is_active=True
            ).first()

            dati = sezione.dati.filter(consultazione_id=consultazione_id).first()

            result.append({
                'sezione_id': sezione.id,
                'numero': sezione.numero,
                'comune': sezione.comune.nome,
                'indirizzo': sezione.indirizzo,
                'assigned': assignment is not None,
                'rdl_email': assignment.user.email if assignment else None,
                'has_data': dati.is_complete if dati else False,
                'is_verified': dati.is_verified if dati else False,
                'affluenza': dati.affluenza_percentuale if dati else None,
            })

        return Response(result)


class KPIIncidentsView(APIView):
    """
    Incidents breakdown by category and status.

    GET /api/kpi/incidents/?consultazione={id}
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione')

        if not consultazione_id:
            consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
            if not consultazione:
                return Response({'error': 'No active consultation'}, status=404)
            consultazione_id = consultazione.id

        incidents = IncidentReport.objects.filter(consultazione_id=consultazione_id)

        by_category = incidents.values('category').annotate(count=Count('id'))
        by_severity = incidents.values('severity').annotate(count=Count('id'))
        by_status = incidents.values('status').annotate(count=Count('id'))

        return Response({
            'by_category': list(by_category),
            'by_severity': list(by_severity),
            'by_status': list(by_status),
            'total': incidents.count(),
        })
