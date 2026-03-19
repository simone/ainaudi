"""
Management command per verificare quali RDL hanno PDF pre-generato su GCS.

Uso:
    python manage.py check_pdf_rdl --consultazione 1
    python manage.py check_pdf_rdl --consultazione 1 --only-missing
"""
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db.models import Q
from delegations.models import ProcessoDesignazione, DesignazioneRDL
import hashlib


class Command(BaseCommand):
    help = 'Verifica quali RDL hanno PDF pre-generato su GCS'

    def add_arguments(self, parser):
        parser.add_argument('--consultazione', type=int, required=True,
                          help='ID consultazione')
        parser.add_argument('--only-missing', action='store_true',
                          help='Mostra solo RDL senza PDF')

    def handle(self, *args, **options):
        consultazione_id = options['consultazione']
        only_missing = options['only_missing']

        # Trova processi APPROVATO/INVIATO
        processi = ProcessoDesignazione.objects.filter(
            consultazione_id=consultazione_id,
            stato__in=['APPROVATO', 'INVIATO']
        ).select_related('comune', 'consultazione')

        if not processi.exists():
            self.stderr.write(self.style.ERROR('Nessun processo APPROVATO/INVIATO'))
            return

        self.stdout.write('='*80)
        self.stdout.write('VERIFICA PDF RDL SU GCS')
        self.stdout.write('='*80)
        self.stdout.write(f'Consultazione: {processi[0].consultazione.nome}')
        self.stdout.write(f'Processi: {processi.count()}')

        # Raccogli RDL unici
        rdl_map = {}
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
                            'nome': f'{des.effettivo_nome} {des.effettivo_cognome}',
                        }

                # Supplente
                if des.supplente_email:
                    email = des.supplente_email.lower()
                    if email not in rdl_map:
                        rdl_map[email] = {
                            'processo': processo,
                            'nome': f'{des.supplente_nome} {des.supplente_cognome}',
                        }

        self.stdout.write(f'RDL unici: {len(rdl_map)}\n')

        # Verifica PDF su GCS
        self.stdout.write('Verifica PDF su GCS...\n')
        con_pdf = []
        senza_pdf = []

        for email, data in rdl_map.items():
            processo = data['processo']
            email_hash = hashlib.md5(email.encode()).hexdigest()[:12]
            gcs_path = f'deleghe/processi/processo_{processo.id}/rdl/{email_hash}.pdf'

            try:
                exists = default_storage.exists(gcs_path)
            except Exception:
                exists = False

            if exists:
                con_pdf.append((email, data['nome']))
            else:
                senza_pdf.append((email, data['nome']))

        # Riepilogo
        self.stdout.write('='*80)
        self.stdout.write('RIEPILOGO')
        self.stdout.write('='*80)
        self.stdout.write(f'Con PDF: {len(con_pdf)}')
        self.stdout.write(f'Senza PDF: {len(senza_pdf)}')

        # Lista
        if not only_missing and con_pdf:
            self.stdout.write('\n' + self.style.SUCCESS('RDL con PDF:'))
            for email, nome in con_pdf[:20]:
                self.stdout.write(f'  ✓ {email} - {nome}')
            if len(con_pdf) > 20:
                self.stdout.write(f'  ... e altri {len(con_pdf) - 20}')

        if senza_pdf:
            self.stdout.write('\n' + self.style.WARNING('RDL senza PDF (email NON verranno inviate):'))
            for email, nome in senza_pdf:
                self.stdout.write(f'  ✗ {email} - {nome}')

        if not senza_pdf:
            self.stdout.write('\n' + self.style.SUCCESS('Tutti gli RDL hanno PDF!'))
