"""
Management command per invio email bulk agli RDL con designazioni.

Replica la logica di campaign/services/mass_email_service.py ma:
- Destinatari: RDL con designazioni CONFERMATA (invece di RdlRegistration)
- Allega PDF pre-generato se disponibile
- Context template: rdl.* + designazioni.* + pdf_url

Uso:
    scripts/django-shell-production.sh send_bulk_rdl_emails --consultazione 1 --template 5 --dry-run
    scripts/django-shell-production.sh send_bulk_rdl_emails --consultazione 1 --template 5
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.template.loader import render_to_string
from django.core.files.storage import default_storage
from django.db.models import Q
from elections.models import ConsultazioneElettorale
from delegations.models import ProcessoDesignazione, DesignazioneRDL
from campaign.models import EmailTemplate, MassEmailLog, RdlRegistration
import hashlib
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Invia email bulk agli RDL con designazioni CONFERMATA usando EmailTemplate dal DB'

    def add_arguments(self, parser):
        parser.add_argument('--consultazione', type=int, required=True,
                          help='ID consultazione')
        parser.add_argument('--template', type=int, required=True,
                          help='ID EmailTemplate dal database')
        parser.add_argument('--dry-run', action='store_true',
                          help='Invia email di test a s.federici@gmail.com')
        parser.add_argument('--force-resend', action='store_true',
                          help='Reinvia anche a chi ha già ricevuto')

    def handle(self, *args, **options):
        consultazione_id = options['consultazione']
        template_id = options['template']
        dry_run = options['dry_run']
        force_resend = options['force_resend']

        # Carica consultazione
        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Consultazione {consultazione_id} non trovata'))
            return

        # Carica template email
        try:
            email_template = EmailTemplate.objects.get(id=template_id)
        except EmailTemplate.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'EmailTemplate {template_id} non trovato'))
            return

        self.stdout.write('\n' + '='*80)
        self.stdout.write('INVIO BULK EMAIL RDL')
        self.stdout.write('='*80)
        self.stdout.write(f'Consultazione: {consultazione.nome}')
        self.stdout.write(f'Template: {email_template.nome}')
        self.stdout.write(f'Oggetto: {email_template.oggetto}')

        # Trova processi APPROVATO/INVIATO
        processi = ProcessoDesignazione.objects.filter(
            consultazione_id=consultazione_id,
            stato__in=['APPROVATO', 'INVIATO']
        ).select_related('comune', 'consultazione')

        if not processi.exists():
            self.stderr.write(self.style.ERROR('Nessun processo APPROVATO/INVIATO'))
            return

        self.stdout.write(f'Processi: {processi.count()}')

        # Raccogli RDL unici con designazioni
        rdl_map = {}  # email -> {processo, designazioni, nome, pdf_info, rdl_registration}

        for processo in processi:
            designazioni = DesignazioneRDL.objects.filter(
                processo=processo,
                stato='CONFERMATA',
                is_attiva=True
            ).select_related('sezione__comune')

            for des in designazioni:
                # Effettivo
                if des.effettivo_email:
                    email = des.effettivo_email.lower()
                    if email not in rdl_map:
                        rdl_map[email] = {
                            'processo': processo,
                            'designazioni': [],
                            'nome': f'{des.effettivo_nome} {des.effettivo_cognome}',
                            'rdl_registration': None,
                        }
                    rdl_map[email]['designazioni'].append(des)

                # Supplente
                if des.supplente_email:
                    email = des.supplente_email.lower()
                    if email not in rdl_map:
                        rdl_map[email] = {
                            'processo': processo,
                            'designazioni': [],
                            'nome': f'{des.supplente_nome} {des.supplente_cognome}',
                            'rdl_registration': None,
                        }
                    rdl_map[email]['designazioni'].append(des)

        self.stdout.write(f'RDL unici: {len(rdl_map)}')

        # Arricchisci con RdlRegistration se esiste (per context template rdl.*)
        # Fai una sola query invece di N query individuali
        all_emails = list(rdl_map.keys())
        registrations = RdlRegistration.objects.filter(email__in=all_emails)
        registrations_by_email = {r.email: r for r in registrations}

        for email, data in rdl_map.items():
            data['rdl_registration'] = registrations_by_email.get(email)

        # Escludi già inviati (MassEmailLog) - una sola query invece di N
        if not force_resend:
            rdl_registration_ids = [
                data['rdl_registration'].id
                for data in rdl_map.values()
                if data['rdl_registration']
            ]

            if rdl_registration_ids:
                already_sent_logs = MassEmailLog.objects.filter(
                    template_id=template_id,
                    rdl_registration_id__in=rdl_registration_ids
                ).values_list('rdl_registration__email', flat=True)

                already_sent_emails = set(already_sent_logs)

                if already_sent_emails:
                    rdl_map = {email: data for email, data in rdl_map.items()
                              if email not in already_sent_emails}
                    self.stdout.write(f'\nEsclusi già inviati: {len(already_sent_emails)}')

        if not rdl_map:
            self.stdout.write(self.style.SUCCESS('\nTutte le email già inviate!'))
            return

        # Riepilogo
        self.stdout.write('\n' + '='*80)
        self.stdout.write('RIEPILOGO')
        self.stdout.write('='*80)
        self.stdout.write(f'Email da inviare: {len(rdl_map)}')
        self.stdout.write(f'Solo RDL con PDF allegato (altri skippati)')

        if dry_run:
            self.stdout.write('\n' + '='*80)
            self.stdout.write('DRY RUN - Test a s.federici@gmail.com')
            self.stdout.write('='*80)

            test_email = 's.federici@gmail.com'
            test_data = rdl_map.get(test_email)

            if test_data:
                self.stdout.write(f'Nome: {test_data["nome"]}')
                self.stdout.write(f'Designazioni: {len(test_data["designazioni"])}')

                try:
                    success = self._send_email(
                        email=test_email,
                        data=test_data,
                        email_template=email_template,
                        is_test=True,
                        user_email='command'
                    )

                    if success:
                        self.stdout.write(self.style.SUCCESS('\n✓ Email di test inviata'))
                    else:
                        self.stderr.write(self.style.ERROR('\n✗ Errore invio'))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'\n✗ Errore: {e}'))
                    logger.error(f'Errore test: {e}', exc_info=True)
            else:
                self.stdout.write(self.style.WARNING(
                    f'{test_email} non ha designazioni in questa consultazione'
                ))

            self.stdout.write('\n' + self.style.WARNING('Dry run completato'))
            return

        # Conferma
        self.stdout.write('\n' + self.style.WARNING(
            f'Verranno inviate {len(rdl_map)} email. Continuare? [y/N]'
        ))
        confirm = input().strip().lower()
        if confirm != 'y':
            self.stdout.write('Annullato')
            return

        # Invio
        self.stdout.write('\n' + '='*80)
        self.stdout.write('INVIO IN CORSO')
        self.stdout.write('='*80)

        sent = 0
        skipped = 0
        failed = 0
        start_time = time.time()

        for i, (email, data) in enumerate(rdl_map.items(), 1):
            try:
                success = self._send_email(
                    email=email,
                    data=data,
                    email_template=email_template,
                    is_test=False,
                    user_email='command'
                )

                if success:
                    sent += 1
                    status = '✓'
                    message = f'{i}/{len(rdl_map)} {status} {email}'
                elif success is False:
                    # False = skipped (no PDF)
                    skipped += 1
                    status = '⊘'
                    message = f'{i}/{len(rdl_map)} {status} {email} - PDF non trovato, skippata'
                else:
                    failed += 1
                    status = '✗'
                    message = f'{i}/{len(rdl_map)} {status} {email}'

                elapsed = time.time() - start_time
                rate = sent / elapsed if elapsed > 0 else 0
                if success:
                    message += f' ({rate:.1f} email/s)'

                self.stdout.write(message)

                # Rate limiting: 10 email/sec (solo per quelle inviate)
                if success:
                    time.sleep(0.1)

            except Exception as e:
                failed += 1
                self.stderr.write(f'{i}/{len(rdl_map)} ✗ {email}: {e}')
                logger.error(f'Errore {email}: {e}', exc_info=True)

        # Riepilogo
        elapsed_total = time.time() - start_time
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('COMPLETATO'))
        self.stdout.write('='*80)
        self.stdout.write(f'Inviate: {sent}')
        self.stdout.write(f'Skippate (no PDF): {skipped}')
        self.stdout.write(f'Fallite: {failed}')
        self.stdout.write(f'Tempo: {elapsed_total:.1f}s')
        if sent > 0:
            self.stdout.write(f'Media: {sent/elapsed_total:.1f} email/s')

    def _send_email(self, email, data, email_template, is_test, user_email):
        """Invia email usando la stessa logica di mass_email_service._send_single_email"""
        processo = data['processo']
        designazioni = data['designazioni']
        nome = data['nome']
        rdl_registration = data['rdl_registration']

        # Calcola PDF path/url
        email_hash = hashlib.md5(email.encode()).hexdigest()[:12]
        pdf_path = f'deleghe/processi/processo_{processo.id}/rdl/{email_hash}.pdf'
        pdf_url = f'https://storage.googleapis.com/ainaudi-documents/{pdf_path}'

        # Prova a scaricare PDF da GCS - se non esiste skippa l'email
        pdf_bytes = None
        pdf_exists = False
        try:
            with default_storage.open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            pdf_exists = True
        except Exception:
            # PDF non esiste - skippa questa email
            logger.info(f'PDF non trovato per {email}, email skippata')
            return False

        # Build context (variabili template)
        context = {
            'designazioni': {
                'n': len(designazioni),
                'pdf_url': pdf_url if pdf_exists else None,
                'ha_pdf': pdf_exists,
            },
            'consultazione': {
                'nome': processo.consultazione.nome if processo.consultazione else 'N/A',
            },
        }

        # Aggiungi rdl.* se disponibile RdlRegistration
        if rdl_registration:
            context['rdl'] = {
                'nome': rdl_registration.nome,
                'cognome': rdl_registration.cognome,
                'full_name': rdl_registration.full_name,
                'email': rdl_registration.email,
                'telefono': rdl_registration.telefono,
                'comune': rdl_registration.comune.nome if rdl_registration.comune else '',
                'municipio': str(rdl_registration.municipio) if rdl_registration.municipio else '',
                'comune_residenza': rdl_registration.comune_residenza,
                'indirizzo_residenza': rdl_registration.indirizzo_residenza,
                'seggio_preferenza': rdl_registration.seggio_preferenza,
                'status': rdl_registration.status,
            }
        else:
            # Fallback: dati dalla designazione
            nome_parts = nome.split()
            context['rdl'] = {
                'nome': nome_parts[0] if nome_parts else '',
                'cognome': ' '.join(nome_parts[1:]) if len(nome_parts) > 1 else '',
                'full_name': nome,
                'email': email,
                'telefono': '',
                'comune': processo.comune.nome if processo.comune else '',
                'municipio': '',
                'comune_residenza': '',
                'indirizzo_residenza': '',
                'seggio_preferenza': '',
                'status': 'APPROVED',
            }

        # Render template (stessa logica di mass_email_service)
        rendered_body = Template(email_template.corpo).render(Context(context))
        rendered_subject = Template(email_template.oggetto).render(Context(context))

        # Wrap in HTML template
        html_message = render_to_string('campaign/email/mass_email_wrapper.html', {
            'body_content': rendered_body,
        })

        # Invia email
        try:
            from django.core.mail import EmailMultiAlternatives

            msg = EmailMultiAlternatives(
                subject=rendered_subject,
                body=rendered_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_message, "text/html")

            # Allega PDF (già scaricato)
            if pdf_bytes:
                rdl_nome = context['rdl']['nome'].upper().replace(' ', '_')
                rdl_cognome = context['rdl']['cognome'].upper().replace(' ', '_')
                filename = f'NOMINA_RDL_{rdl_nome}_{rdl_cognome}_2026.pdf'
                msg.attach(
                    filename,
                    pdf_bytes,
                    'application/pdf'
                )

            msg.send(fail_silently=False)
            stato = 'SUCCESS'
            errore = ''

        except Exception as e:
            stato = 'FAILED'
            errore = str(e)
            logger.error(f'Errore invio {email}: {e}')

        # Log (solo se non test e se esiste RdlRegistration)
        if not is_test and rdl_registration:
            MassEmailLog.objects.create(
                template=email_template,
                rdl_registration=rdl_registration,
                stato=stato,
                errore=errore,
                sent_by_email=user_email,
            )

        return stato == 'SUCCESS'
