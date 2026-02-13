"""
Management command to populate TemplateType instances with default schemas.

Legge gli example_schema dalle classi in template_types.py (unica fonte di verita').

Usage:
    python manage.py populate_template_types
"""
from django.core.management.base import BaseCommand
from documents.models import TemplateType
from documents.template_types import DesignationSingleType, DesignationMultiType


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
            self.stdout.write(self.style.SUCCESS(f'Created: {delegation_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'Updated: {delegation_type}'))

        # 2. DESIGNATION_SINGLE - schema dalla registry Python
        designation_single_type, created = TemplateType.objects.update_or_create(
            code='DESIGNATION_SINGLE',
            defaults={
                'name': DesignationSingleType.name,
                'description': DesignationSingleType.description,
                'default_schema': DesignationSingleType.example_schema,
                'default_merge_mode': TemplateType.MergeMode.SINGLE_DOC_PER_RECORD,
                'use_case': (
                    'Usare questo tipo quando si generano documenti separati per ogni sezione.\n'
                    'Output: N PDF (uno per sezione).\n'
                    'Struttura: delegato + sezione/comune/indirizzo + effettivo + supplente (piatto, no loop).\n'
                    'Esempio: SubDelegato con 10 sezioni -> 10 PDF individuali.'
                ),
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created: {designation_single_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'Updated: {designation_single_type}'))

        # 3. DESIGNATION_MULTI - schema dalla registry Python
        designation_multi_type, created = TemplateType.objects.update_or_create(
            code='DESIGNATION_MULTI',
            defaults={
                'name': DesignationMultiType.name,
                'description': DesignationMultiType.description,
                'default_schema': DesignationMultiType.example_schema,
                'default_merge_mode': TemplateType.MergeMode.MULTI_PAGE_LOOP,
                'use_case': (
                    'Usare questo tipo quando si genera un unico documento riepilogativo.\n'
                    'Output: 1 PDF con tabella di N righe (stampa unione).\n'
                    'Struttura: delegato + designazioni[] (array con loop, ogni item ha effettivo/supplente nested).\n'
                    'Esempio: SubDelegato con 10 sezioni -> 1 PDF con tabella di 10 righe.\n'
                    'Supporta multi-pagina: configurare page=0 (prima pagina) e page=1 (pagine successive).'
                ),
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created: {designation_multi_type}'))
        else:
            self.stdout.write(self.style.WARNING(f'Updated: {designation_multi_type}'))

        self.stdout.write(self.style.SUCCESS('\nTemplateType population completed!'))
        self.stdout.write(f'\n  {TemplateType.objects.count()} template types in database')
