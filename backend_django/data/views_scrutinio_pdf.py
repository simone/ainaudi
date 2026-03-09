"""
View for generating printable scrutinio data collection forms (PDF).
"""
import logging
from rest_framework import permissions
from rest_framework.views import APIView
from django.http import HttpResponse
from django.db.models import Q

from elections.models import ConsultazioneElettorale, SchedaElettorale
from territory.models import SezioneElettorale
from delegations.models import DesignazioneRDL
from .scrutinio_pdf import generate_scrutinio_form

logger = logging.getLogger(__name__)


def get_consultazione_attiva():
    return ConsultazioneElettorale.objects.filter(is_attiva=True).first()


class ScrutinioFormPDFView(APIView):
    """
    Generate a printable PDF form for scrutinio data collection.

    GET /api/scrutinio/form-pdf
    GET /api/scrutinio/form-pdf?consultazione_id=1

    Only returns sections assigned to the user as RDL (effettivo or supplente).
    Delegates use the app directly and don't need paper forms.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        consultazione_id = request.query_params.get('consultazione_id')

        if consultazione_id:
            try:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
            except ConsultazioneElettorale.DoesNotExist:
                return HttpResponse('Consultazione non trovata', status=404)
        else:
            consultazione = get_consultazione_attiva()

        if not consultazione:
            return HttpResponse('Nessuna consultazione attiva', status=404)

        # Only RDL sections from confirmed designations
        sezioni_ids = set(
            DesignazioneRDL.objects.filter(
                Q(effettivo_email=request.user.email) | Q(supplente_email=request.user.email),
                is_attiva=True,
                stato='CONFERMATA',
            ).filter(
                Q(delegato__consultazione=consultazione) |
                Q(sub_delega__delegato__consultazione=consultazione)
            ).values_list('sezione_id', flat=True)
        )

        if not sezioni_ids:
            return HttpResponse('Nessuna sezione assegnata come RDL', status=404)

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
