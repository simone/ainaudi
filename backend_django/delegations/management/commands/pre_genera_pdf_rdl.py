"""
Pre-genera PDF individuali per ogni RDL di un processo e li salva su GCS.

Uso:
    python manage.py pre_genera_pdf_rdl 34
    python manage.py pre_genera_pdf_rdl 34 --dry-run
    python manage.py pre_genera_pdf_rdl --consultazione 1
"""
from django.core.management.base import BaseCommand
from delegations.models import ProcessoDesignazione
from delegations.services import PDFExtractionService


class Command(BaseCommand):
    help = 'Pre-genera PDF individuali per ogni RDL su GCS'

    def add_arguments(self, parser):
        parser.add_argument('processo_id', nargs='?', type=int, help='ID del processo')
        parser.add_argument('--consultazione', type=int, help='ID consultazione (usa ultimo processo APPROVATO)')
        parser.add_argument('--dry-run', action='store_true', help='Mostra quanti RDL senza generare')

    def handle(self, *args, **options):
        processo = self._get_processo(options)
        if not processo:
            return

        self.stdout.write(f"Processo {processo.id}: {processo.stato} - {processo.comune}")
        self.stdout.write(f"Consultazione: {processo.consultazione}")
        self.stdout.write(f"Designazioni: {processo.n_designazioni}")
        self.stdout.write(f"Documento: {processo.documento_individuale.name if processo.documento_individuale else 'MANCANTE'}")

        if not processo.documento_individuale:
            self.stderr.write(self.style.ERROR("PDF individuale non generato"))
            return

        # Conta RDL
        designazioni = processo.designazioni.filter(stato='CONFERMATA', is_attiva=True)
        emails = set()
        for des in designazioni:
            if des.effettivo_email:
                emails.add(des.effettivo_email)
            if des.supplente_email:
                emails.add(des.supplente_email)

        self.stdout.write(f"RDL distinti: {len(emails)}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("Dry run, nessun file generato"))
            return

        self.stdout.write(self.style.WARNING(f"Avvio pre-generazione per {len(emails)} RDL..."))

        result = PDFExtractionService.pre_genera_pdf_rdl(processo)

        self.stdout.write(self.style.SUCCESS(
            f"Completato: {result['generati']}/{result['totale_rdl']} generati, "
            f"{result['errori']} errori"
        ))

        if result['dettagli']:
            for d in result['dettagli']:
                self.stderr.write(self.style.ERROR(f"  {d}"))

    def _get_processo(self, options):
        if options['processo_id']:
            try:
                return ProcessoDesignazione.objects.get(id=options['processo_id'])
            except ProcessoDesignazione.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Processo {options['processo_id']} non trovato"))
                return None

        if options['consultazione']:
            processo = ProcessoDesignazione.objects.filter(
                consultazione_id=options['consultazione'],
                stato__in=['APPROVATO', 'INVIATO']
            ).order_by('-id').first()
            if not processo:
                self.stderr.write(self.style.ERROR(
                    f"Nessun processo APPROVATO per consultazione {options['consultazione']}"
                ))
                return None
            return processo

        self.stderr.write(self.style.ERROR("Specifica processo_id o --consultazione"))
        return None
