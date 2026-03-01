"""
Service per invio email massivo agli RDL registrati.

Pattern identico a delegations/services/email_service.py:
thread daemon + Redis progress + rate limiting.
"""
import logging
import re
import time

from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Variabili disponibili nei template email
AVAILABLE_VARIABLES = [
    {'name': 'rdl.nome', 'description': 'Nome dell\'RDL'},
    {'name': 'rdl.cognome', 'description': 'Cognome dell\'RDL'},
    {'name': 'rdl.full_name', 'description': 'Nome e cognome completo'},
    {'name': 'rdl.email', 'description': 'Email dell\'RDL'},
    {'name': 'rdl.telefono', 'description': 'Telefono dell\'RDL'},
    {'name': 'rdl.comune', 'description': 'Comune operativo'},
    {'name': 'rdl.municipio', 'description': 'Municipio (se presente)'},
    {'name': 'rdl.comune_residenza', 'description': 'Comune di residenza'},
    {'name': 'rdl.indirizzo_residenza', 'description': 'Indirizzo di residenza'},
    {'name': 'rdl.seggio_preferenza', 'description': 'Seggio/plesso di preferenza'},
    {'name': 'rdl.status', 'description': 'Stato registrazione (PENDING/APPROVED/REJECTED)'},
]


def _build_rdl_context(rdl):
    """Costruisce il context dict per un RDL reale."""
    return {
        'rdl': {
            'nome': rdl.nome,
            'cognome': rdl.cognome,
            'full_name': rdl.full_name,
            'email': rdl.email,
            'telefono': rdl.telefono,
            'comune': rdl.comune.nome if rdl.comune else '',
            'municipio': str(rdl.municipio) if rdl.municipio else '',
            'comune_residenza': rdl.comune_residenza,
            'indirizzo_residenza': rdl.indirizzo_residenza,
            'seggio_preferenza': rdl.seggio_preferenza,
            'status': rdl.status,
        }
    }


def _build_preview_context():
    """Costruisce il context dict con dati finti per preview."""
    return {
        'rdl': {
            'nome': 'Mario',
            'cognome': 'Rossi',
            'full_name': 'Mario Rossi',
            'email': 'mario.rossi@esempio.it',
            'telefono': '333 1234567',
            'comune': 'Roma',
            'municipio': 'Municipio I',
            'comune_residenza': 'Roma',
            'indirizzo_residenza': 'Via del Corso 1',
            'seggio_preferenza': 'Scuola Dante Alighieri',
            'status': 'APPROVED',
        }
    }


def _validate_template_body(corpo):
    """
    Valida il corpo del template: solo variabili {{ }} e filtri | permessi.
    Rifiuta tag {% %} per sicurezza.
    """
    if re.search(r'\{%', corpo):
        raise ValueError(
            'Il corpo del template non può contenere tag {% %}. '
            'Usa solo variabili {{ rdl.nome }} e filtri {{ rdl.nome|upper }}.'
        )


def render_template_string(template_str, context):
    """Renderizza una stringa template Django con il context dato."""
    tpl = Template(template_str)
    return tpl.render(Context(context))


def render_preview(corpo, oggetto=''):
    """
    Renderizza il template con dati finti per preview.
    Ritorna il body renderizzato wrappato nel template HTML brandizzato.
    """
    context = _build_preview_context()
    rendered_body = render_template_string(corpo, context)
    rendered_subject = render_template_string(oggetto, context) if oggetto else ''

    # Wrap nel template HTML brandizzato
    html = render_to_string('campaign/email/mass_email_wrapper.html', {
        'body_content': rendered_body,
    })

    return {
        'subject': rendered_subject,
        'html': html,
    }


def get_recipients_info(template_id, filters, consultazione_id=None):
    """
    Calcola info destinatari per un invio:
    - total: RDL che matchano i filtri
    - already_sent: RDL a cui è già stata inviata questa mail
    - new_recipients: RDL nuovi (total - already_sent)
    """
    from campaign.models import RdlRegistration, MassEmailLog

    qs = RdlRegistration.objects.all()

    # Default: only APPROVED RDLs (unless status explicitly specified)
    status_filter = filters.get('status', 'APPROVED')
    if status_filter:
        qs = qs.filter(status=status_filter)

    # Filtri territorio
    if filters.get('comune'):
        qs = qs.filter(comune_id=filters['comune'])
    if filters.get('municipio'):
        qs = qs.filter(municipio_id=filters['municipio'])
    if filters.get('regione'):
        qs = qs.filter(comune__provincia__regione_id=filters['regione'])
    if filters.get('provincia'):
        qs = qs.filter(comune__provincia_id=filters['provincia'])

    total = qs.count()

    # Conta quanti hanno già ricevuto questo template (tra i destinatari attuali)
    already_sent = 0
    if template_id:
        # Filtra per RDL nel queryset attuale (con territorio applicato)
        already_sent_ids = set(
            MassEmailLog.objects.filter(
                template_id=template_id,
                rdl_registration__in=qs  # Filtra per destinatari con filtri territorio applicati
            ).values_list('rdl_registration_id', flat=True)
        )
        already_sent = len(already_sent_ids)

    return {
        'total': total,
        'already_sent': already_sent,
        'new_recipients': total - already_sent,
    }


def send_mass_email_batch(template_id, filters, user_email, consultazione_id=None, batch_size=50):
    """
    Invia un batch di email (max 50) sincronamente.

    Returns:
        {
            'sent': numero email inviate in questo batch,
            'remaining': numero email ancora da inviare,
            'total': numero totale destinatari
        }
    """
    from campaign.models import RdlRegistration, EmailTemplate, MassEmailLog

    # Recupera template
    try:
        template = EmailTemplate.objects.get(id=template_id)
    except EmailTemplate.DoesNotExist:
        return {'sent': 0, 'remaining': 0, 'total': 0, 'error': 'Template non trovato'}

    # Build queryset destinatari
    qs = RdlRegistration.objects.select_related('comune', 'municipio')

    # Default: only APPROVED RDLs (unless status explicitly specified)
    status_filter = filters.get('status', 'APPROVED')
    if status_filter:
        qs = qs.filter(status=status_filter)

    if filters.get('comune'):
        qs = qs.filter(comune_id=filters['comune'])
    if filters.get('municipio'):
        qs = qs.filter(municipio_id=filters['municipio'])
    if filters.get('regione'):
        qs = qs.filter(comune__provincia__regione_id=filters['regione'])
    if filters.get('provincia'):
        qs = qs.filter(comune__provincia_id=filters['provincia'])

    # Escludi RDL già inviate per questo template (ma solo tra i destinatari attuali)
    # IMPORTANTE: filtriamo per qs per considerare solo i destinatari nel municipio/provincia/region selezionato
    already_sent_ids = set(
        MassEmailLog.objects.filter(
            template_id=template_id,
            rdl_registration__in=qs,  # Filtra per RDL nel queryset attuale
        ).values_list('rdl_registration_id', flat=True)
    )

    # Filtra destinatari da inviare
    recipients_to_send = [rdl for rdl in qs if rdl.id not in already_sent_ids]
    total_recipients = len(recipients_to_send)

    # Invia batch (max 50)
    batch = recipients_to_send[:batch_size]
    sent = 0
    failed = 0

    for rdl in batch:
        success = _send_single_email(template, rdl, user_email)
        if success:
            sent += 1
        else:
            failed += 1

        # Rate limiting: 14 email/sec per SES quota
        time.sleep(1/14)

    remaining = total_recipients - len(already_sent_ids) - sent

    logger.info(f"Batch email: {sent} sent, {remaining} remaining (template: {template.nome})")

    return {
        'sent': sent,
        'remaining': max(0, remaining),
        'total': total_recipients,
    }




def _send_single_email(template, rdl, user_email):
    """Invia una singola email ad un RDL e crea il MassEmailLog."""
    from campaign.models import MassEmailLog

    try:
        context = _build_rdl_context(rdl)

        rendered_body = render_template_string(template.corpo, context)
        rendered_subject = render_template_string(template.oggetto, context)

        html_message = render_to_string('campaign/email/mass_email_wrapper.html', {
            'body_content': rendered_body,
        })

        send_mail(
            subject=rendered_subject,
            message=rendered_body,  # plain text fallback
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[rdl.email],
            fail_silently=False,
            html_message=html_message,
        )

        MassEmailLog.objects.create(
            template=template,
            rdl_registration=rdl,
            stato='SUCCESS',
            sent_by_email=user_email,
        )

        logger.info(f"Mass email sent to {rdl.email} (template: {template.nome})")
        return True

    except Exception as e:
        logger.error(f"Mass email failed for {rdl.email}: {e}", exc_info=True)

        MassEmailLog.objects.create(
            template=template,
            rdl_registration=rdl,
            stato='FAILED',
            errore=str(e),
            sent_by_email=user_email,
        )
        return False


