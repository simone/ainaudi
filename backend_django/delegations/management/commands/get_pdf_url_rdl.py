"""
Management command per ottenere il link PDF pre-generato di un RDL.

Dato l'email di un RDL, mostra:
- Hash MD5 dell'email
- Link GCS al PDF pre-generato per ogni processo
- Verifica se il file esiste su GCS

Uso:
    python manage.py get_pdf_url_rdl mario.rossi@example.com
    python manage.py get_pdf_url_rdl mario.rossi@example.com --processo 34
    python manage.py get_pdf_url_rdl mario.rossi@example.com --check-exists
"""
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.db.models import Q
from delegations.models import DesignazioneRDL, ProcessoDesignazione
import hashlib


class Command(BaseCommand):
    help = 'Mostra il link PDF pre-generato per un RDL dato il suo email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email del RDL')
        parser.add_argument('--processo', type=int, help='ID processo specifico (opzionale)')
        parser.add_argument('--check-exists', action='store_true',
                          help='Verifica se il file esiste su GCS')

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        processo_id = options['processo']
        check_exists = options['check_exists']

        # Calcola hash
        email_hash = hashlib.md5(email.encode()).hexdigest()[:12]

        self.stdout.write('\n' + '='*80)
        self.stdout.write('PDF RDL - LINK GENERATOR')
        self.stdout.write('='*80)
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Hash MD5: {email_hash}')
        self.stdout.write('='*80)

        # Trova designazioni per questa email
        designazioni_query = DesignazioneRDL.objects.filter(
            Q(effettivo_email=email) | Q(supplente_email=email),
            stato='CONFERMATA',
            is_attiva=True
        ).select_related('processo', 'sezione__comune')

        if processo_id:
            designazioni_query = designazioni_query.filter(processo_id=processo_id)

        designazioni = list(designazioni_query)

        if not designazioni:
            self.stderr.write(self.style.WARNING(
                f'\nNessuna designazione CONFERMATA trovata per {email}'
            ))
            if processo_id:
                self.stderr.write(f'nel processo {processo_id}')
            return

        # Raggruppa per processo
        processi_map = {}
        for des in designazioni:
            processo = des.processo
            if processo.id not in processi_map:
                processi_map[processo.id] = {
                    'processo': processo,
                    'designazioni': [],
                }
            processi_map[processo.id]['designazioni'].append(des)

        self.stdout.write(f'\nProcessi trovati: {len(processi_map)}')

        # Per ogni processo, mostra il link
        for pid, data in sorted(processi_map.items()):
            processo = data['processo']
            designazioni_proc = data['designazioni']

            self.stdout.write('\n' + '-'*80)
            self.stdout.write(f'PROCESSO {processo.id}')
            self.stdout.write('-'*80)
            self.stdout.write(f'Consultazione: {processo.consultazione.nome if processo.consultazione else "N/A"}')
            self.stdout.write(f'Comune: {processo.comune.nome if processo.comune else "N/A"}')
            self.stdout.write(f'Stato: {processo.stato}')
            self.stdout.write(f'Designazioni: {len(designazioni_proc)}')

            # Mostra sezioni
            sezioni = []
            for des in designazioni_proc:
                ruolo = []
                if des.effettivo_email == email:
                    ruolo.append('EFFETTIVO')
                if des.supplente_email == email:
                    ruolo.append('SUPPLENTE')
                sezioni.append(f"Sez. {des.sezione.numero} ({'/'.join(ruolo)})")

            self.stdout.write(f'Sezioni: {", ".join(sezioni[:5])}{"..." if len(sezioni) > 5 else ""}')

            # Costruisci link GCS
            gcs_path = f'deleghe/processi/processo_{processo.id}/rdl/{email_hash}.pdf'
            gcs_url = f'https://storage.googleapis.com/ainaudi-documents/{gcs_path}'

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'GCS Path: {gcs_path}'))
            self.stdout.write(self.style.SUCCESS(f'URL: {gcs_url}'))

            # Verifica esistenza se richiesto
            if check_exists:
                try:
                    exists = default_storage.exists(gcs_path)
                    if exists:
                        size = default_storage.size(gcs_path)
                        self.stdout.write(self.style.SUCCESS(
                            f'✓ File esiste su GCS ({size:,} bytes ~ {size/1024/1024:.2f} MB)'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            '✗ File NON esiste su GCS - eseguire pre_genera_pdf_rdl'
                        ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Errore verifica: {e}'))

        # Riepilogo comando per generare
        self.stdout.write('\n' + '='*80)
        self.stdout.write('COMANDI UTILI')
        self.stdout.write('='*80)
        if len(processi_map) == 1:
            pid = list(processi_map.keys())[0]
            self.stdout.write(f'Genera PDF: python manage.py pre_genera_pdf_rdl {pid}')
        else:
            self.stdout.write('Genera PDF per tutti i processi:')
            for pid in sorted(processi_map.keys()):
                self.stdout.write(f'  python manage.py pre_genera_pdf_rdl {pid}')

        self.stdout.write('')
