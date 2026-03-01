"""
Email service per invio notifiche RDL.
Gestisce rendering template, invio email asincrono con Redis, e tracciamento progress.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from typing import Dict, Tuple
import logging
import time

logger = logging.getLogger(__name__)


class RDLEmailService:
    """
    Servizio per invio email agli RDL designati.
    """

    @staticmethod
    def invia_notifiche_processo_batch(processo, user_email: str, batch_size=50):
        """
        Invia un batch di notifiche (max 50) sincronamente.
        Continua dall'ultimo invio.

        Returns:
            {
                'sent': numero email inviate in questo batch,
                'remaining': numero email ancora da inviare,
                'total': numero totale email
            }
        """
        from delegations.models import ProcessoDesignazione, EmailDesignazioneLog
        from django.utils import timezone

        designazioni = processo.designazioni.filter(
            stato='CONFERMATA',
            is_attiva=True
        ).select_related('sezione__comune')

        # Raggruppa per email unica (un RDL può essere effettivo per alcuni seggi e supplente per altri)
        email_groups = {}

        for des in designazioni:
            if des.effettivo_email:
                if des.effettivo_email not in email_groups:
                    email_groups[des.effettivo_email] = {
                        'nome': f"{des.effettivo_nome} {des.effettivo_cognome}",
                        'sezioni_effettivo': [],
                        'sezioni_supplente': []
                    }
                email_groups[des.effettivo_email]['sezioni_effettivo'].append(des.sezione)

            if des.supplente_email:
                if des.supplente_email not in email_groups:
                    email_groups[des.supplente_email] = {
                        'nome': f"{des.supplente_nome} {des.supplente_cognome}",
                        'sezioni_effettivo': [],
                        'sezioni_supplente': []
                    }
                email_groups[des.supplente_email]['sezioni_supplente'].append(des.sezione)

        # Escludi email già inviate per questo processo
        already_sent_emails = set(
            EmailDesignazioneLog.objects.filter(
                processo_id=processo.id,
                stato='SUCCESS'
            ).values_list('destinatario_email', flat=True).distinct()
        )

        # Filtra email da inviare
        emails_to_send = [(email, data) for email, data in email_groups.items()
                          if email not in already_sent_emails]
        total_emails = len(emails_to_send)

        # Invia batch (max 50)
        batch = emails_to_send[:batch_size]
        sent = 0
        failed = 0

        for email, data in batch:
            success, log = RDLEmailService._invia_email_rdl(
                processo=processo,
                email=email,
                nome=data['nome'],
                sezioni_effettivo=data['sezioni_effettivo'],
                sezioni_supplente=data['sezioni_supplente'],
                user_email=user_email
            )
            if success:
                sent += 1
            else:
                failed += 1

            # Rate limiting: 14 email/sec per SES quota
            time.sleep(1/14)

        remaining = total_emails - len(already_sent_emails) - sent

        logger.info(f"Batch processo {processo.id}: {sent} sent, {remaining} remaining")

        return {
            'sent': sent,
            'remaining': max(0, remaining),
            'total': total_emails,
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
