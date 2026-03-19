"""
Management command per inviare email agli RDL di una provincia.

Logica:
- PENDING: email di invito a completare la registrazione
- APPROVED: email di conferma + se hanno designazioni CONFERMATA allega link PDF

Rate limiting: 10 email/sec per Amazon SES.

Uso:
    python manage.py send_email_rdl_provincia 58 --consultazione 1
    python manage.py send_email_rdl_provincia 58 --consultazione 1 --dry-run
    python manage.py send_email_rdl_provincia 58 --consultazione 1 --only-with-designations
"""
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Q, Count
from campaign.models import RdlRegistration
from delegations.models import DesignazioneRDL, ProcessoDesignazione
from elections.models import ConsultazioneElettorale
import time
import hashlib
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Invia email agli RDL di una provincia (PENDING o APPROVED con/senza designazioni)'

    def add_arguments(self, parser):
        parser.add_argument('provincia_id', type=int, help='ID della provincia (58=Roma)')
        parser.add_argument('--consultazione', type=int, required=True, help='ID consultazione')
        parser.add_argument('--dry-run', action='store_true', help='Mostra chi riceverà email senza inviarle')
        parser.add_argument('--only-with-designations', action='store_true',
                          help='Solo RDL con designazioni CONFERMATA')
        parser.add_argument('--status', choices=['PENDING', 'APPROVED', 'ALL'], default='ALL',
                          help='Filtra per status (default: ALL)')

    def handle(self, *args, **options):
        provincia_id = options['provincia_id']
        consultazione_id = options['consultazione']
        dry_run = options['dry_run']
        only_with_designations = options['only_with_designations']
        status_filter = options['status']

        # Verifica consultazione
        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Consultazione {consultazione_id} non trovata'))
            return

        # Trova processo APPROVATO o INVIATO per la consultazione
        processo = ProcessoDesignazione.objects.filter(
            consultazione_id=consultazione_id,
            stato__in=['APPROVATO', 'INVIATO']
        ).order_by('-id').first()

        if not processo:
            self.stderr.write(self.style.WARNING(
                f'Nessun processo APPROVATO per consultazione {consultazione_id}'
            ))
            processo = None

        self.stdout.write(f'\nConsultazione: {consultazione.nome}')
        if processo:
            self.stdout.write(f'Processo: {processo.id} ({processo.stato})')
        else:
            self.stdout.write(self.style.WARNING('Nessun processo trovato - solo email di invito'))

        # Filtra RDL per provincia
        rdl_query = RdlRegistration.objects.filter(
            comune__provincia_id=provincia_id
        ).select_related('comune', 'municipio')

        # Filtra per status
        if status_filter != 'ALL':
            rdl_query = rdl_query.filter(status=status_filter)

        rdl_list = list(rdl_query)
        self.stdout.write(f'\nRDL trovati in provincia {provincia_id}: {len(rdl_list)}')

        # Per ogni RDL, controlla se ha designazioni
        rdl_with_data = []

        for rdl in rdl_list:
            designazioni = None
            pdf_url = None

            if processo:
                designazioni = DesignazioneRDL.objects.filter(
                    Q(effettivo_email=rdl.email) | Q(supplente_email=rdl.email),
                    processo=processo,
                    stato='CONFERMATA',
                    is_attiva=True
                )

                if designazioni.exists():
                    # Calcola hash per URL GCS
                    email_hash = hashlib.md5(rdl.email.lower().encode()).hexdigest()[:12]
                    pdf_url = f'https://storage.googleapis.com/ainaudi-documents/deleghe/processi/processo_{processo.id}/rdl/{email_hash}.pdf'

            rdl_with_data.append({
                'rdl': rdl,
                'designazioni': designazioni,
                'pdf_url': pdf_url,
                'n_designazioni': designazioni.count() if designazioni else 0
            })

        # Filtra solo con designazioni se richiesto
        if only_with_designations:
            rdl_with_data = [r for r in rdl_with_data if r['n_designazioni'] > 0]
            self.stdout.write(f'Con designazioni CONFERMATA: {len(rdl_with_data)}')

        if not rdl_with_data:
            self.stdout.write(self.style.WARNING('Nessun RDL da processare'))
            return

        # Riepilogo
        self.stdout.write('\n' + '='*80)
        self.stdout.write('RIEPILOGO')
        self.stdout.write('='*80)

        pending_count = sum(1 for r in rdl_with_data if r['rdl'].status == 'PENDING')
        approved_count = sum(1 for r in rdl_with_data if r['rdl'].status == 'APPROVED')
        with_pdf_count = sum(1 for r in rdl_with_data if r['pdf_url'])

        self.stdout.write(f'PENDING: {pending_count}')
        self.stdout.write(f'APPROVED: {approved_count}')
        self.stdout.write(f'Con PDF designazione: {with_pdf_count}')
        self.stdout.write(f'TOTALE EMAIL DA INVIARE: {len(rdl_with_data)}')

        if dry_run:
            self.stdout.write('\n' + '='*80)
            self.stdout.write('DRY RUN - Esempio email:')
            self.stdout.write('='*80)
            for i, data in enumerate(rdl_with_data[:5]):
                rdl = data['rdl']
                self.stdout.write(f"\n{i+1}. {rdl.nome} {rdl.cognome} <{rdl.email}>")
                self.stdout.write(f"   Status: {rdl.status}")
                self.stdout.write(f"   Comune: {rdl.comune.nome}")
                if data['n_designazioni'] > 0:
                    self.stdout.write(f"   Designazioni: {data['n_designazioni']}")
                    self.stdout.write(f"   PDF: {data['pdf_url']}")

            if len(rdl_with_data) > 5:
                self.stdout.write(f"\n... e altri {len(rdl_with_data) - 5} RDL")

            self.stdout.write('\n' + self.style.WARNING('Dry run - nessuna email inviata'))
            return

        # Conferma invio
        self.stdout.write('\n' + self.style.WARNING(
            f'Verranno inviate {len(rdl_with_data)} email. Continuare? [y/N]'
        ))
        confirm = input().strip().lower()
        if confirm != 'y':
            self.stdout.write('Annullato')
            return

        # Invio email
        self.stdout.write('\n' + '='*80)
        self.stdout.write('INVIO EMAIL')
        self.stdout.write('='*80)

        sent = 0
        failed = 0

        for i, data in enumerate(rdl_with_data, 1):
            rdl = data['rdl']

            try:
                success = self._send_email(
                    rdl=rdl,
                    consultazione=consultazione,
                    processo=processo,
                    n_designazioni=data['n_designazioni'],
                    pdf_url=data['pdf_url']
                )

                if success:
                    sent += 1
                    self.stdout.write(f'{i}/{len(rdl_with_data)} ✓ {rdl.email}')
                else:
                    failed += 1
                    self.stderr.write(f'{i}/{len(rdl_with_data)} ✗ {rdl.email}')

                # Rate limiting: 10 email/sec
                time.sleep(0.1)

            except Exception as e:
                failed += 1
                self.stderr.write(f'{i}/{len(rdl_with_data)} ✗ {rdl.email}: {str(e)}')

        # Riepilogo finale
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS(f'COMPLETATO'))
        self.stdout.write('='*80)
        self.stdout.write(f'Inviate: {sent}')
        self.stdout.write(f'Fallite: {failed}')

    def _send_email(self, rdl, consultazione, processo, n_designazioni, pdf_url):
        """Invia email a singolo RDL."""

        # Prepara context per template
        context = {
            'nome': rdl.nome,
            'cognome': rdl.cognome,
            'nome_completo': f'{rdl.nome} {rdl.cognome}',
            'consultazione': consultazione.nome,
            'app_url': settings.FRONTEND_URL,
            'status': rdl.status,
            'is_pending': rdl.status == 'PENDING',
            'is_approved': rdl.status == 'APPROVED',
            'ha_designazioni': n_designazioni > 0,
            'n_designazioni': n_designazioni,
            'pdf_url': pdf_url,
            'comune': rdl.comune.nome,
        }

        # Subject dinamico
        if rdl.status == 'PENDING':
            subject = f'Completa la tua registrazione RDL - {consultazione.nome}'
        elif n_designazioni > 0:
            subject = f'Le tue designazioni RDL - {consultazione.nome}'
        else:
            subject = f'Registrazione RDL confermata - {consultazione.nome}'

        # Render template
        html_message = render_to_string(
            'campaign/email/invito_rdl_provincia.html',
            context
        )

        text_message = render_to_string(
            'campaign/email/invito_rdl_provincia.txt',
            context
        )

        # Invia
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[rdl.email],
        )
        msg.attach_alternative(html_message, "text/html")

        try:
            msg.send(fail_silently=False)
            return True
        except Exception as e:
            logger.error(f'Errore invio email a {rdl.email}: {e}')
            return False
