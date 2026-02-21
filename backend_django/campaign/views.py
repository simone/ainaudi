"""
API views per Email Templates e Mass Email.

Endpoints sotto /api/rdl/ con permission CanManageRDL.
"""
import logging

from django.template import Template, TemplateSyntaxError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import CanManageMassEmail
from campaign.models import EmailTemplate, MassEmailLog
from campaign.services.mass_email_service import (
    AVAILABLE_VARIABLES,
    render_preview,
    render_template_string,
    get_recipients_info,
    send_mass_email_async,
    get_task_progress,
    _validate_template_body,
    _build_preview_context,
)

logger = logging.getLogger(__name__)


def _serialize_template(tpl):
    """Serializza un EmailTemplate per la risposta JSON."""
    return {
        'id': tpl.id,
        'nome': tpl.nome,
        'oggetto': tpl.oggetto,
        'corpo': tpl.corpo,
        'consultazione': tpl.consultazione_id,
        'created_by_email': tpl.created_by_email,
        'created_at': tpl.created_at.isoformat() if tpl.created_at else None,
        'updated_at': tpl.updated_at.isoformat() if tpl.updated_at else None,
        'n_invii': tpl.n_invii,
        'has_been_sent': tpl.has_been_sent,
    }


class EmailTemplateListView(APIView):
    """
    GET  /api/rdl/email-templates/     - Lista template (filtro consultazione)
    POST /api/rdl/email-templates/     - Crea template
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def get(self, request):
        qs = EmailTemplate.objects.all()
        consultazione = request.query_params.get('consultazione')
        if consultazione:
            qs = qs.filter(consultazione_id=consultazione)
        return Response([_serialize_template(t) for t in qs])

    def post(self, request):
        data = request.data
        nome = data.get('nome', '').strip()
        oggetto = data.get('oggetto', '').strip()
        corpo = data.get('corpo', '').strip()

        if not nome or not oggetto or not corpo:
            return Response(
                {'error': 'nome, oggetto e corpo sono obbligatori'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate template body
        try:
            _validate_template_body(corpo)
            Template(corpo)
            Template(oggetto)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except TemplateSyntaxError as e:
            return Response(
                {'error': f'Errore di sintassi nel template: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tpl = EmailTemplate.objects.create(
            nome=nome,
            oggetto=oggetto,
            corpo=corpo,
            consultazione_id=data.get('consultazione'),
            created_by_email=request.user.email,
        )
        return Response(_serialize_template(tpl), status=status.HTTP_201_CREATED)


class EmailTemplateDetailView(APIView):
    """
    GET    /api/rdl/email-templates/<id>/  - Dettaglio template
    PUT    /api/rdl/email-templates/<id>/  - Modifica template
    DELETE /api/rdl/email-templates/<id>/  - Elimina (solo se mai inviato)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def get(self, request, pk):
        try:
            tpl = EmailTemplate.objects.get(id=pk)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_template(tpl))

    def put(self, request, pk):
        try:
            tpl = EmailTemplate.objects.get(id=pk)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        nome = data.get('nome', '').strip()
        oggetto = data.get('oggetto', '').strip()
        corpo = data.get('corpo', '').strip()

        if not nome or not oggetto or not corpo:
            return Response(
                {'error': 'nome, oggetto e corpo sono obbligatori'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            _validate_template_body(corpo)
            Template(corpo)
            Template(oggetto)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except TemplateSyntaxError as e:
            return Response(
                {'error': f'Errore di sintassi nel template: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tpl.nome = nome
        tpl.oggetto = oggetto
        tpl.corpo = corpo
        if 'consultazione' in data:
            tpl.consultazione_id = data['consultazione']
        tpl.save()
        return Response(_serialize_template(tpl))

    def delete(self, request, pk):
        try:
            tpl = EmailTemplate.objects.get(id=pk)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        if tpl.has_been_sent:
            return Response(
                {'error': 'Impossibile eliminare un template già utilizzato per invii'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tpl.delete()
        return Response({'ok': True})


class EmailTemplatePreviewView(APIView):
    """
    POST /api/rdl/email-templates/<id>/preview/  - Preview con dati finti
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def post(self, request, pk):
        try:
            tpl = EmailTemplate.objects.get(id=pk)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        try:
            result = render_preview(tpl.corpo, tpl.oggetto)
        except Exception as e:
            return Response(
                {'error': f'Errore nel rendering del template: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)


class EmailTemplateTestSendView(APIView):
    """
    POST /api/rdl/email-templates/<id>/test-send/  - Invia email di test all'utente loggato
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def post(self, request, pk):
        from django.core.mail import send_mail as django_send_mail
        from django.conf import settings
        from django.template.loader import render_to_string

        try:
            tpl = EmailTemplate.objects.get(id=pk)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        try:
            preview_context = _build_preview_context()
            rendered_body = render_template_string(tpl.corpo, preview_context)
            rendered_subject = render_template_string(tpl.oggetto, preview_context)

            html_message = render_to_string('campaign/email/mass_email_wrapper.html', {
                'body_content': rendered_body,
            })

            django_send_mail(
                subject=f'[TEST] {rendered_subject}',
                message=rendered_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
                html_message=html_message,
            )

            return Response({'ok': True, 'sent_to': request.user.email})

        except Exception as e:
            return Response(
                {'error': f'Errore invio test: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailTemplatePreviewInlineView(APIView):
    """
    POST /api/rdl/email-templates/preview-inline/  - Preview inline (senza salvare)
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def post(self, request):
        corpo = request.data.get('corpo', '')
        oggetto = request.data.get('oggetto', '')

        try:
            _validate_template_body(corpo)
            result = render_preview(corpo, oggetto)
        except Exception as e:
            return Response(
                {'error': f'Errore nel rendering: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)


class EmailTemplateVariablesView(APIView):
    """
    GET /api/rdl/email-templates/variables/  - Lista variabili disponibili
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def get(self, request):
        return Response(AVAILABLE_VARIABLES)


class MassEmailRecipientsInfoView(APIView):
    """
    POST /api/rdl/mass-email/recipients-info/  - Conteggi destinatari + deduplica
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def post(self, request):
        template_id = request.data.get('template_id')
        filters = request.data.get('filters', {})
        consultazione_id = request.data.get('consultazione_id')

        if not template_id:
            return Response(
                {'error': 'template_id è obbligatorio'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            EmailTemplate.objects.get(id=template_id)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        info = get_recipients_info(template_id, filters, consultazione_id)
        return Response(info)


class MassEmailSendView(APIView):
    """
    POST /api/rdl/mass-email/send/  - Avvia invio asincrono
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def post(self, request):
        template_id = request.data.get('template_id')
        filters = request.data.get('filters', {})
        consultazione_id = request.data.get('consultazione_id')

        if not template_id:
            return Response(
                {'error': 'template_id è obbligatorio'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            EmailTemplate.objects.get(id=template_id)
        except EmailTemplate.DoesNotExist:
            return Response({'error': 'Template non trovato'}, status=status.HTTP_404_NOT_FOUND)

        # Check there are recipients
        info = get_recipients_info(template_id, filters, consultazione_id)
        if info['new_recipients'] == 0:
            return Response(
                {'error': 'Nessun nuovo destinatario per questo template'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_id = send_mass_email_async(
                template_id, filters, request.user.email, consultazione_id
            )
        except RuntimeError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'task_id': task_id})


class MassEmailProgressView(APIView):
    """
    GET /api/rdl/mass-email/progress/<task_id>/  - Poll progresso
    """
    permission_classes = [permissions.IsAuthenticated, CanManageMassEmail]

    def get(self, request, task_id):
        progress = get_task_progress(task_id)
        return Response(progress)
