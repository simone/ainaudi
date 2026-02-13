"""
Rigenera i PDF di tutti i processi di designazione confermati (APPROVATO).

Uso:
    python manage.py rigenera_pdf_designazioni
    python manage.py rigenera_pdf_designazioni --processo-id 42
    python manage.py rigenera_pdf_designazioni --dry-run
"""
from django.core.management.base import BaseCommand
from delegations.models import ProcessoDesignazione


class Command(BaseCommand):
    help = 'Rigenera i PDF (individuale + cumulativo) dei processi di designazione confermati.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--processo-id',
            type=int,
            help='Rigenera solo un processo specifico (per ID)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra quali processi verrebbero rigenerati senza farlo',
        )

    def handle(self, *args, **options):
        processo_id = options.get('processo_id')
        dry_run = options.get('dry_run', False)

        qs = ProcessoDesignazione.objects.filter(
            stato__in=['APPROVATO', 'INVIATO'],
        )

        if processo_id:
            qs = qs.filter(id=processo_id)

        processi = qs.select_related(
            'template_individuale', 'template_cumulativo', 'comune'
        )

        if not processi.exists():
            self.stdout.write(self.style.WARNING('Nessun processo confermato trovato.'))
            return

        self.stdout.write(f'Trovati {processi.count()} processi da rigenerare.')

        if dry_run:
            for p in processi:
                n_desig = p.designazioni.count()
                self.stdout.write(
                    f'  Processo #{p.id} - {p.comune} - '
                    f'stato={p.stato} - {n_desig} designazioni - '
                    f'ind={bool(p.template_individuale)} cum={bool(p.template_cumulativo)}'
                )
            self.stdout.write(self.style.SUCCESS('Dry run completato.'))
            return

        # Import qui per evitare import circolari
        from documents.pdf_generator import PDFGenerator, generate_pdf
        from django.core.files.base import ContentFile
        from django.utils import timezone
        from PyPDF2 import PdfWriter, PdfReader
        import io

        success = 0
        errors = 0

        for processo in processi:
            self.stdout.write(f'\nProcesso #{processo.id} ({processo.comune})...')

            try:
                # Rigenera individuale
                if processo.template_individuale:
                    designazioni = processo.designazioni.all().select_related(
                        'sezione', 'sezione__comune', 'sezione__municipio'
                    ).order_by('sezione__numero')

                    writer = PdfWriter()
                    for designazione in designazioni:
                        data = {
                            'delegato': processo.dati_delegato,
                            'designazioni': [{
                                'effettivo_cognome': designazione.effettivo_cognome,
                                'effettivo_nome': designazione.effettivo_nome,
                                'effettivo_data_nascita': designazione.effettivo_data_nascita,
                                'effettivo_luogo_nascita': designazione.effettivo_luogo_nascita,
                                'effettivo_domicilio': designazione.effettivo_domicilio,
                                'supplente_cognome': designazione.supplente_cognome or '',
                                'supplente_nome': designazione.supplente_nome or '',
                                'supplente_data_nascita': designazione.supplente_data_nascita,
                                'supplente_luogo_nascita': designazione.supplente_luogo_nascita or '',
                                'supplente_domicilio': designazione.supplente_domicilio or '',
                                'sezione_numero': designazione.sezione.numero,
                                'sezione_indirizzo': designazione.sezione.indirizzo or '',
                                'comune_nome': designazione.sezione.comune.nome if designazione.sezione.comune else '',
                            }]
                        }
                        generator = PDFGenerator(processo.template_individuale.template_file, data)
                        pdf_bytes = generator.generate_from_template(processo.template_individuale)
                        pdf_reader = PdfReader(pdf_bytes)
                        for page in pdf_reader.pages:
                            writer.add_page(page)

                    output = io.BytesIO()
                    writer.write(output)
                    output.seek(0)
                    processo.documento_individuale.save(
                        f'processo_{processo.id}_individuale.pdf',
                        ContentFile(output.read()),
                        save=False
                    )
                    processo.data_generazione_individuale = timezone.now()
                    self.stdout.write(self.style.SUCCESS(
                        f'  Individuale: {designazioni.count()} pagine rigenerate'
                    ))

                # Rigenera cumulativo
                if processo.template_cumulativo:
                    designazioni = processo.designazioni.all().select_related(
                        'sezione', 'sezione__comune', 'sezione__municipio'
                    ).order_by('sezione__numero')

                    data = {
                        'delegato': processo.dati_delegato,
                        'designazioni': [
                            {
                                'effettivo_cognome': d.effettivo_cognome,
                                'effettivo_nome': d.effettivo_nome,
                                'effettivo_data_nascita': d.effettivo_data_nascita,
                                'effettivo_luogo_nascita': d.effettivo_luogo_nascita,
                                'effettivo_domicilio': d.effettivo_domicilio,
                                'supplente_cognome': d.supplente_cognome or '',
                                'supplente_nome': d.supplente_nome or '',
                                'supplente_data_nascita': d.supplente_data_nascita,
                                'supplente_luogo_nascita': d.supplente_luogo_nascita or '',
                                'supplente_domicilio': d.supplente_domicilio or '',
                                'sezione_numero': d.sezione.numero,
                                'sezione_indirizzo': d.sezione.indirizzo or '',
                                'comune_nome': d.sezione.comune.nome if d.sezione.comune else '',
                            }
                            for d in designazioni
                        ]
                    }
                    pdf_bytes = generate_pdf(processo.template_cumulativo, data)
                    processo.documento_cumulativo.save(
                        f'processo_{processo.id}_cumulativo.pdf',
                        ContentFile(pdf_bytes.read()),
                        save=False
                    )
                    processo.data_generazione_cumulativo = timezone.now()
                    self.stdout.write(self.style.SUCCESS(
                        f'  Cumulativo: rigenerato'
                    ))

                processo.save()

                # Invalida cache Redis per i PDF estratti
                try:
                    from core.redis_client import get_redis_client
                    redis_client = get_redis_client()
                    if redis_client:
                        import fnmatch
                        keys = redis_client.keys('pdf_nomina:*')
                        if keys:
                            redis_client.delete(*keys)
                            self.stdout.write(f'  Cache Redis invalidata ({len(keys)} chiavi)')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Cache Redis non invalidata: {e}'))

                success += 1

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f'  ERRORE: {e}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Completato: {success} processi rigenerati, {errors} errori.'
        ))
