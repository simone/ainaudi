"""
View for generating printable scrutinio data collection forms (PDF).
"""
import logging
from rest_framework import permissions
from rest_framework.views import APIView
from django.http import HttpResponse
from django.db.models import Q

from core.permissions import HasScrutinioAccess
from .models import SectionAssignment
from elections.models import ConsultazioneElettorale, SchedaElettorale
from territory.models import SezioneElettorale
from delegations.models import DesignazioneRDL
from delegations.permissions import get_sezioni_filter_for_user, get_user_delegation_roles
from .scrutinio_pdf import generate_scrutinio_form

logger = logging.getLogger(__name__)


def get_consultazione_attiva():
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class ScrutinioFormPDFView(APIView):
    """
    Generate a printable PDF form for scrutinio data collection.

    GET /api/scrutinio/form-pdf
    GET /api/scrutinio/form-pdf?consultazione_id=1
    GET /api/scrutinio/form-pdf?sezione_id=42  (single section)

    Returns PDF with one page per assigned section, pre-filled with
    section info and empty boxes for each data field.
    """
    permission_classes = [permissions.IsAuthenticated, HasScrutinioAccess]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione_id')
        sezione_id = request.query_params.get('sezione_id')

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                return HttpResponse('Consultazione non trovata', status=404)
        else:
            consultazione = get_consultazione_attiva()

        if not consultazione:
            return HttpResponse('Nessuna consultazione attiva', status=404)

        # Get user's sections (same logic as ScrutinioMieiSeggiLightView)
        sezioni_ids = set()

        # RDL: sections from confirmed designations
        designazioni = DesignazioneRDL.objects.filter(
            Q(effettivo_email=request.user.email) | Q(supplente_email=request.user.email),
            is_attiva=True,
            stato='CONFERMATA',
        ).filter(
            Q(delegato__consultazione=consultazione) |
            Q(sub_delega__delegato__consultazione=consultazione)
        ).values_list('sezione_id', flat=True)
        sezioni_ids.update(designazioni)

        # Delegato/SubDelegato: territory sections
        roles = get_user_delegation_roles(request.user, consultazione.id)
        if roles['is_delegato'] or roles['is_sub_delegato']:
            sezioni_filter = get_sezioni_filter_for_user(request.user, consultazione.id)
            if sezioni_filter is not None and sezioni_filter != Q():
                mapped = SectionAssignment.objects.filter(
                    sezione__in=SezioneElettorale.objects.filter(sezioni_filter, is_attiva=True),
                    consultazione=consultazione,
                ).values_list('sezione_id', flat=True).distinct()
                sezioni_ids.update(mapped)

        # Filter to single section if requested
        if sezione_id:
            sezione_id = int(sezione_id)
            if sezione_id not in sezioni_ids:
                return HttpResponse('Sezione non accessibile', status=403)
            sezioni_ids = {sezione_id}

        if not sezioni_ids:
            return HttpResponse('Nessuna sezione assegnata', status=404)

        # Load section details
        sezioni = SezioneElettorale.objects.filter(
            id__in=sezioni_ids
        ).select_related('comune', 'municipio').order_by('comune__nome', 'numero')

        # Load schede for this consultazione
        schede = SchedaElettorale.objects.filter(
            tipo_elezione__consultazione=consultazione
        ).order_by('ordine')

        schede_data = [
            {
                'nome': s.nome,
                'colore': s.colore or '',
                'schema_voti': s.schema_voti or {},
            }
            for s in schede
        ]

        # Build section data for PDF
        sezioni_with_schede = []
        for sez in sezioni:
            sezioni_with_schede.append({
                'numero': str(sez.numero),
                'comune': sez.comune.nome if sez.comune else '',
                'municipio': sez.municipio.nome if sez.municipio else '',
                'indirizzo': sez.indirizzo or '',
                'denominazione': sez.denominazione or '',
                'schede': schede_data,
            })

        logger.info(
            f"ScrutinioFormPDF: user={request.user.email} "
            f"consultazione={consultazione.id} sezioni={len(sezioni_with_schede)}"
        )

        # Generate PDF
        pdf_buffer = generate_scrutinio_form(consultazione, sezioni_with_schede)

        # Return as downloadable PDF
        filename = f"modulo_scrutinio_{consultazione.id}.pdf"
        if len(sezioni_with_schede) == 1:
            filename = f"modulo_scrutinio_sez{sezioni_with_schede[0]['numero']}.pdf"

        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
