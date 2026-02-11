"""
Email service per invio notifiche RDL.
Gestisce rendering template, invio email asincrono con Redis, e tracciamento progress.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Tuple
import logging
import threading
import time

from core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RDLEmailService:
    """
    Servizio per invio email agli RDL designati.
    """

    @staticmethod
    def invia_notifiche_processo_async(processo, user_email: str) -> str:
        """
        Avvia invio asincrono email a tutti gli RDL di un processo.

        Args:
            processo: ProcessoDesignazione instance
            user_email: Email utente che ha avviato l'invio

        Returns:
            task_id: ID univoco per tracking progress
        """
        import uuid
        task_id = f"email_task_{processo.id}_{uuid.uuid4().hex[:8]}"

        r = get_redis_client()
        if not r:
            raise RuntimeError("Redis client not available")

        # Salva stato iniziale in Redis
        r.hset(
            task_id,
            mapping={
                'status': 'STARTED',
                'current': '0',
                'total': '0',
                'sent': '0',
                'failed': '0',
                'processo_id': str(processo.id),
                'user_email': user_email
            }
        )
        r.expire(task_id, 3600)  # TTL 1 ora

        # Salva task_id corrente per questo processo (per polling)
        task_key = f"email_task_current_{processo.id}"
        r.setex(task_key, 3600, task_id)  # TTL 1 ora

        # Avvia thread worker
        thread = threading.Thread(
            target=RDLEmailService._worker_invio_email,
            args=(task_id, processo.id, user_email),
            daemon=True
        )
        thread.start()

        logger.info(f"Task email avviato: {task_id} per processo {processo.id}")

        return task_id

    @staticmethod
    def _worker_invio_email(task_id: str, processo_id: int, user_email: str):
        """
        Worker thread per invio email in background con rate limiting.
        """
        try:
            from delegations.models import ProcessoDesignazione, EmailDesignazioneLog
            from django.utils import timezone
            from django.db.models import Q

            r = get_redis_client()
            if not r:
                logger.error("Redis not available in worker thread")
                return

            processo = ProcessoDesignazione.objects.get(id=processo_id)

            designazioni = processo.designazioni.filter(
                stato='CONFERMATA',
                is_attiva=True
            ).select_related('sezione__comune')

            # STEP 1: Raggruppa designazioni per email unica
            # IMPORTANTE: Un RDL può essere effettivo per alcune sezioni E supplente per altre
            email_groups = {}  # {email: {'nome': str, 'sezioni_effettivo': [], 'sezioni_supplente': []}}

            for des in designazioni:
                # Aggiungi effettivo
                if des.effettivo_email:
                    if des.effettivo_email not in email_groups:
                        email_groups[des.effettivo_email] = {
                            'nome': f"{des.effettivo_nome} {des.effettivo_cognome}",
                            'sezioni_effettivo': [],
                            'sezioni_supplente': []
                        }
                    email_groups[des.effettivo_email]['sezioni_effettivo'].append(des.sezione)

                # Aggiungi supplente
                if des.supplente_email:
                    if des.supplente_email not in email_groups:
                        email_groups[des.supplente_email] = {
                            'nome': f"{des.supplente_nome} {des.supplente_cognome}",
                            'sezioni_effettivo': [],
                            'sezioni_supplente': []
                        }
                    email_groups[des.supplente_email]['sezioni_supplente'].append(des.sezione)

            # STEP 2: Conta totale email da inviare (UNA per email unica)
            total_emails = len(email_groups)

            r.hset(task_id, 'total', str(total_emails))
            r.hset(task_id, 'status', 'PROGRESS')

            current = 0
            sent = 0
            failed = 0
            logs = []

            # STEP 3: Invia una email per ogni indirizzo unico
            for email, data in email_groups.items():
                success, log = RDLEmailService._invia_email_rdl(
                    processo=processo,
                    email=email,
                    nome=data['nome'],
                    sezioni_effettivo=data['sezioni_effettivo'],
                    sezioni_supplente=data['sezioni_supplente']
                )

                if success:
                    sent += 1
                else:
                    failed += 1

                logs.append(log)
                current += 1

                # Update progress in Redis
                r.hset(task_id, 'current', str(current))
                r.hset(task_id, 'sent', str(sent))
                r.hset(task_id, 'failed', str(failed))

                # Rate limiting: 5 email/sec (0.2s interval)
                time.sleep(0.2)

            # Salva log nel database
            for log_data in logs:
                EmailDesignazioneLog.objects.create(
                    processo=processo,
                    sent_by_email=user_email,
                    **log_data
                )

            # Aggiorna processo
            processo.email_inviate_at = timezone.now()
            processo.email_inviate_da = user_email
            processo.n_email_inviate = sent
            processo.n_email_fallite = failed

            if failed == 0:
                processo.stato = 'INVIATO'

            processo.save()

            # Mark task as completed
            r.hset(task_id, 'status', 'SUCCESS')
            r.expire(task_id, 86400)  # Keep for 24h for audit

            logger.info(f"Task {task_id} completato: {sent} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            r.hset(task_id, 'status', 'FAILURE')
            r.hset(task_id, 'error', str(e))
            r.expire(task_id, 3600)

    @staticmethod
    def get_task_progress(task_id: str) -> Dict:
        """
        Recupera progress di un task da Redis.

        Returns:
            {
                'status': 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE',
                'current': int,
                'total': int,
                'sent': int,
                'failed': int,
                'error': str (se FAILURE)
            }
        """
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
            'error': data.get('error', '')
        }

    @staticmethod
    def _invia_email_rdl(
        processo,
        email: str,
        nome: str,
        sezioni_effettivo: list,
        sezioni_supplente: list
    ) -> Tuple[bool, Dict]:
        """
        Invia email a singolo RDL (che può avere sia sezioni come effettivo che come supplente).

        Args:
            processo: ProcessoDesignazione instance
            email: Email destinatario
            nome: Nome completo RDL
            sezioni_effettivo: Lista sezioni come EFFETTIVO
            sezioni_supplente: Lista sezioni come SUPPLENTE

        Returns:
            (success: bool, log: dict)
        """
        try:
            # Determina ruoli
            ha_effettivo = len(sezioni_effettivo) > 0
            ha_supplente = len(sezioni_supplente) > 0

            # Tipo RDL per log (può essere entrambi)
            if ha_effettivo and ha_supplente:
                tipo_rdl_log = 'EFFETTIVO+SUPPLENTE'
            elif ha_effettivo:
                tipo_rdl_log = 'EFFETTIVO'
            else:
                tipo_rdl_log = 'SUPPLENTE'

            # Prepara dati per template
            context = {
                'nome': nome.split()[0] if nome else 'RDL',  # Solo il nome (non cognome)
                'nome_completo': nome,
                'consultazione': processo.consultazione.nome if processo.consultazione else 'N/A',
                'app_url': settings.FRONTEND_URL,
                # Sezioni per ruolo
                'sezioni_effettivo': sezioni_effettivo,
                'sezioni_supplente': sezioni_supplente,
                'n_sezioni_effettivo': len(sezioni_effettivo),
                'n_sezioni_supplente': len(sezioni_supplente),
                # Flags per template
                'ha_effettivo': ha_effettivo,
                'ha_supplente': ha_supplente,
                'ha_entrambi': ha_effettivo and ha_supplente,
            }

            # Totale sezioni (per subject e saluto)
            context['n_sezioni_totali'] = len(sezioni_effettivo) + len(sezioni_supplente)

            # Subject
            subject = f"Conferma Designazione RDL - {processo.consultazione.nome if processo.consultazione else 'Consultazione'}"

            # LOG DETTAGLIATO PER DEVELOPMENT
            logger.info("=" * 80)
            logger.info(f"📧 INVIO EMAIL RDL - Processo #{processo.id}")
            logger.info("=" * 80)
            logger.info(f"Destinatario: {nome} <{email}>")
            logger.info(f"Tipo RDL: {tipo_rdl_log}")
            logger.info(f"Consultazione: {context['consultazione']}")
            logger.info(f"Totale sezioni: {context['n_sezioni_totali']}")
            if ha_effettivo:
                logger.info(f"  🟢 Sezioni come EFFETTIVO ({len(sezioni_effettivo)}):")
                for sez in sezioni_effettivo:
                    logger.info(f"     - Sez. {sez.numero}: {sez.indirizzo}, {sez.comune.nome}")
            if ha_supplente:
                logger.info(f"  🟡 Sezioni come SUPPLENTE ({len(sezioni_supplente)}):")
                for sez in sezioni_supplente:
                    logger.info(f"     - Sez. {sez.numero}: {sez.indirizzo}, {sez.comune.nome}")
            logger.info(f"Subject: {subject}")
            logger.info(f"From: {settings.DEFAULT_FROM_EMAIL}")
            logger.info(f"Backend EMAIL: {settings.EMAIL_BACKEND}")
            logger.info("=" * 80)

            # Render HTML template
            html_message = render_to_string(
                'delegations/email/notifica_rdl.html',
                context
            )

            # Render plain text fallback
            text_message = render_to_string(
                'delegations/email/notifica_rdl.txt',
                context
            )

            # Invia email (console backend in dev, SMTP in prod)
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
                html_message=html_message,
            )

            logger.info(f"✅ Email inviata con successo a {email} ({tipo_rdl_log})")
            logger.info("")  # Linea vuota per separare

            return True, {
                'destinatario_email': email,
                'destinatario_nome': nome,
                'tipo_rdl': tipo_rdl_log,
                'stato': 'SUCCESS',
                'subject': subject,
                'errore': '',
                'designazione': None  # Nessuna designazione singola, ma multipla
            }

        except Exception as e:
            logger.error(f"❌ Errore invio email a {email}: {e}", exc_info=True)

            return False, {
                'destinatario_email': email,
                'destinatario_nome': nome,
                'tipo_rdl': tipo_rdl_log if 'tipo_rdl_log' in locals() else 'UNKNOWN',
                'stato': 'FAILED',
                'subject': subject if 'subject' in locals() else 'N/A',
                'errore': str(e),
                'designazione': None
            }
