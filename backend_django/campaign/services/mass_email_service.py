"""
Service per invio email massivo agli RDL registrati.

Pattern identico a delegations/services/email_service.py:
thread daemon + Redis progress + rate limiting.
"""
import logging
import re
import threading
import time
import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.template.loader import render_to_string

from core.redis_client import get_redis_client

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

    if consultazione_id:
        qs = qs.filter(consultazione_id=consultazione_id)

    # Filtri territorio
    if filters.get('comune'):
        qs = qs.filter(comune_id=filters['comune'])
    if filters.get('municipio'):
        qs = qs.filter(municipio_id=filters['municipio'])
    if filters.get('regione'):
        qs = qs.filter(comune__provincia__regione_id=filters['regione'])
    if filters.get('provincia'):
        qs = qs.filter(comune__provincia_id=filters['provincia'])

    # Filtro stato
    status_filter = filters.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    total = qs.count()

    # Conta quanti hanno già ricevuto questo template
    already_sent = 0
    if template_id:
        already_sent_ids = set(
            MassEmailLog.objects.filter(
                template_id=template_id,
                rdl_registration__in=qs
            ).values_list('rdl_registration_id', flat=True)
        )
        already_sent = len(already_sent_ids)

    return {
        'total': total,
        'already_sent': already_sent,
        'new_recipients': total - already_sent,
    }


def send_mass_email_async(template_id, filters, user_email, consultazione_id=None):
    """
    Avvia invio asincrono email di massa.
    Ritorna task_id per tracking progress.
    """
    task_id = f"mass_email_{template_id}_{uuid.uuid4().hex[:8]}"

    r = get_redis_client()
    if not r:
        raise RuntimeError("Redis client not available")

    r.hset(task_id, mapping={
        'status': 'STARTED',
        'current': '0',
        'total': '0',
        'sent': '0',
        'failed': '0',
        'skipped': '0',
        'template_id': str(template_id),
        'user_email': user_email,
    })
    r.expire(task_id, 3600)

    thread = threading.Thread(
        target=_worker_send_mass_email,
        args=(task_id, template_id, filters, user_email, consultazione_id),
        daemon=True,
    )
    thread.start()

    logger.info(f"Mass email task started: {task_id} for template {template_id}")
    return task_id


def _worker_send_mass_email(task_id, template_id, filters, user_email, consultazione_id):
    """Worker thread per invio email in background."""
    r = None
    try:
        from campaign.models import EmailTemplate, RdlRegistration, MassEmailLog

        r = get_redis_client()
        if not r:
            logger.error("Redis not available in mass email worker")
            return

        template = EmailTemplate.objects.get(id=template_id)

        # Build queryset
        qs = RdlRegistration.objects.select_related('comune', 'municipio')

        if consultazione_id:
            qs = qs.filter(consultazione_id=consultazione_id)

        if filters.get('comune'):
            qs = qs.filter(comune_id=filters['comune'])
        if filters.get('municipio'):
            qs = qs.filter(municipio_id=filters['municipio'])
        if filters.get('regione'):
            qs = qs.filter(comune__provincia__regione_id=filters['regione'])
        if filters.get('provincia'):
            qs = qs.filter(comune__provincia_id=filters['provincia'])

        status_filter = filters.get('status', '')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Exclude already sent
        already_sent_ids = set(
            MassEmailLog.objects.filter(
                template_id=template_id,
            ).values_list('rdl_registration_id', flat=True)
        )
        recipients = [rdl for rdl in qs if rdl.id not in already_sent_ids]

        total = len(recipients)
        r.hset(task_id, 'total', str(total))
        r.hset(task_id, 'status', 'PROGRESS')

        current = 0
        sent = 0
        failed = 0

        for rdl in recipients:
            success = _send_single_email(template, rdl, user_email)

            if success:
                sent += 1
            else:
                failed += 1

            current += 1
            r.hset(task_id, mapping={
                'current': str(current),
                'sent': str(sent),
                'failed': str(failed),
            })

            # Rate limiting: 5 email/sec
            time.sleep(0.2)

        r.hset(task_id, 'status', 'SUCCESS')
        r.expire(task_id, 86400)

        logger.info(f"Mass email task {task_id} completed: {sent} sent, {failed} failed")

    except Exception as e:
        logger.error(f"Mass email task {task_id} failed: {e}", exc_info=True)
        if r:
            r.hset(task_id, 'status', 'FAILURE')
            r.hset(task_id, 'error', str(e))
            r.expire(task_id, 3600)


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


def get_task_progress(task_id):
    """Recupera progress di un task da Redis."""
    r = get_redis_client()
    if not r:
        return {'status': 'NOT_FOUND', 'error': 'Redis not available'}

    data = r.hgetall(task_id)
    if not data:
        return {'status': 'NOT_FOUND'}

    return {
        'status': data.get('status'),
        'current': int(data.get('current', '0')),
        'total': int(data.get('total', '0')),
        'sent': int(data.get('sent', '0')),
        'failed': int(data.get('failed', '0')),
        'skipped': int(data.get('skipped', '0')),
        'error': data.get('error', ''),
    }
