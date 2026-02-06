"""
Management command to populate TemplateType instances with default schemas.

Usage:
    python manage.py populate_template_types
"""
from django.core.management.base import BaseCommand
from documents.models import TemplateType


class Command(BaseCommand):
    help = 'Populate TemplateType instances with default schemas'

    def handle(self, *args, **options):
        self.stdout.write('Populating TemplateType instances...')

        # 1. DELEGATION - Delega Sub-Delegato
        delegation_schema = {
            "delegato": {
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "email": "mario.rossi@m5s.it",
                "telefono": "+39 123456789",
                "luogo_nascita": "Roma",
                "data_nascita": "1980-01-15",
                "carica_display": "Deputato",
                "circoscrizione": "Lazio 1",
                "data_nomina": "2024-01-01"
            },
            "subdelegato": {
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "email": "anna.bianchi@example.com",
                "telefono": "+39 987654321",
                "luogo_nascita": "Milano",
                "data_nascita": "1985-06-15",
                "domicilio": "Via Roma 1, Milano (MI)",
                "tipo_documento": "Carta d'identità",
                "numero_documento": "AB123456",
                "data_delega": "2024-02-01",
                "territorio": "Milano e provincia",
                "delegato_nome": "Rossi Mario"
            }
        }

        delegation_type, created = TemplateType.objects.update_or_create(
            code='DELEGATION',
            defaults={
                'name': 'Delega Sub-Delegato',
                'description': 'Template per documenti di delega da Delegato a SubDelegato',
                'default_schema': delegation_schema,
                'default_merge_mode': TemplateType.MergeMode.SINGLE_DOC_PER_RECORD,
                'use_case': (
                    'Usare questo tipo quando si genera un documento di sub-delega.\n'
                    'Output: 1 PDF per sub-delega.\n'
                    'Struttura: delegato + subdelegato con campi semplici (no loop).'
                ),
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {delegation_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Updated: {delegation_type}'))

        # 2. DESIGNATION_SINGLE - Designazione RDL Singola (un PDF per sezione)
        designation_single_schema = {
            "delegato": {
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "carica_display": "Deputato"
            },
            "subdelegato": {
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "territorio": "Milano e provincia"
            },
            "designazione": {
                "sezione_id": 1,
                "sezione_numero": "001",
                "sezione_indirizzo": "Via Roma 1, Milano",
                "effettivo_cognome": "Verdi",
                "effettivo_nome": "Luigi",
                "effettivo_nome_completo": "Verdi Luigi",
                "effettivo_email": "luigi.verdi@example.com",
                "effettivo_telefono": "+39 111222333",
                "supplente_cognome": "Gialli",
                "supplente_nome": "Maria",
                "supplente_nome_completo": "Gialli Maria",
                "supplente_email": "maria.gialli@example.com",
                "supplente_telefono": "+39 444555666"
            }
        }

        designation_single_type, created = TemplateType.objects.update_or_create(
            code='DESIGNATION_SINGLE',
            defaults={
                'name': 'Designazione RDL Singola',
                'description': 'Template per designazione RDL - un documento per sezione',
                'default_schema': designation_single_schema,
                'default_merge_mode': TemplateType.MergeMode.SINGLE_DOC_PER_RECORD,
                'use_case': (
                    'Usare questo tipo quando si generano documenti separati per ogni sezione.\n'
                    'Output: N PDF (uno per sezione).\n'
                    'Struttura: delegato + subdelegato + designazione (oggetto, no loop).\n'
                    'Esempio: SubDelegato con 10 sezioni → 10 PDF individuali.'
                ),
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {designation_single_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Updated: {designation_single_type}'))

        # 3. DESIGNATION_MULTI - Designazione RDL Multipla (un PDF con tabella/loop)
        designation_multi_schema = {
            "delegato": {
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "carica_display": "Deputato"
            },
            "subdelegato": {
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "territorio": "Milano e provincia"
            },
            "designazioni": [
                {
                    "sezione_id": 1,
                    "sezione_numero": "001",
                    "sezione_indirizzo": "Via Roma 1, Milano",
                    "effettivo_cognome": "Verdi",
                    "effettivo_nome": "Luigi",
                    "effettivo_nome_completo": "Verdi Luigi",
                    "effettivo_email": "luigi.verdi@example.com",
                    "effettivo_telefono": "+39 111222333",
                    "supplente_cognome": "Gialli",
                    "supplente_nome": "Maria",
                    "supplente_nome_completo": "Gialli Maria",
                    "supplente_email": "maria.gialli@example.com",
                    "supplente_telefono": "+39 444555666"
                },
                {
                    "sezione_id": 2,
                    "sezione_numero": "002",
                    "sezione_indirizzo": "Via Milano 5, Milano",
                    "effettivo_cognome": "Neri",
                    "effettivo_nome": "Paolo",
                    "effettivo_nome_completo": "Neri Paolo",
                    "effettivo_email": "paolo.neri@example.com",
                    "effettivo_telefono": "+39 777888999",
                    "supplente_cognome": "Blu",
                    "supplente_nome": "Carla",
                    "supplente_nome_completo": "Blu Carla",
                    "supplente_email": "carla.blu@example.com",
                    "supplente_telefono": "+39 000111222"
                }
            ]
        }

        designation_multi_type, created = TemplateType.objects.update_or_create(
            code='DESIGNATION_MULTI',
            defaults={
                'name': 'Designazione RDL Riepilogativa',
                'description': 'Template per designazione RDL - documento unico con tabella',
                'default_schema': designation_multi_schema,
                'default_merge_mode': TemplateType.MergeMode.MULTI_PAGE_LOOP,
                'use_case': (
                    'Usare questo tipo quando si genera un unico documento riepilogativo.\n'
                    'Output: 1 PDF con tabella di N righe (stampa unione).\n'
                    'Struttura: delegato + subdelegato + designazioni (array con loop).\n'
                    'Esempio: SubDelegato con 10 sezioni → 1 PDF con tabella di 10 righe.\n'
                    'Supporta multi-pagina: configurare page=0 (prima pagina) e page=1 (pagine successive).'
                ),
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created: {designation_multi_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Updated: {designation_multi_type}'))

        self.stdout.write(self.style.SUCCESS('\n✅ TemplateType population completed!'))
        self.stdout.write('\nSummary:')
        self.stdout.write(f'  - {TemplateType.objects.count()} template types in database')
        self.stdout.write('\nNext steps:')
        self.stdout.write('  1. Run migrations: python manage.py makemigrations && python manage.py migrate')
        self.stdout.write('  2. Assign existing templates to new TemplateType instances')
        self.stdout.write('  3. Update Template Editor to use new structure')
