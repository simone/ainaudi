"""
Management command to populate variables_schema for existing templates.

Usage:
    python manage.py populate_variables_schema
"""
from django.core.management.base import BaseCommand
from documents.models import Template


class Command(BaseCommand):
    help = 'Popola variables_schema per i template esistenti con esempi realistici'

    def handle(self, *args, **options):
        # Schema per template DELEGATION (Sub-Delega)
        delegation_schema = {
            "delegato": {
                "id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "luogo_nascita": "Roma",
                "data_nascita": "1980-01-15",
                "carica": "DEPUTATO",
                "carica_display": "Deputato",
                "circoscrizione": "Lazio 1",
                "data_nomina": "2024-01-01",
                "email": "mario.rossi@m5s.it",
                "telefono": "+39 123456789",
                "territorio": "Regioni: Lazio | Province: Roma, Frosinone",
                "n_sub_deleghe": 5
            },
            "subdelegato": {
                "id": 10,
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "luogo_nascita": "Milano",
                "data_nascita": "1985-06-15",
                "domicilio": "Via Roma 1, 20121 Milano (MI)",
                "tipo_documento": "Carta d'identità",
                "numero_documento": "AB123456",
                "email": "anna.bianchi@example.com",
                "telefono": "+39 987654321",
                "data_delega": "2024-02-01",
                "firma_autenticata": True,
                "autenticatore": "Notaio Giovanni Verdi",
                "tipo_delega": "FIRMA_AUTENTICATA",
                "tipo_delega_display": "Firma Autenticata",
                "puo_designare_direttamente": True,
                "regioni_nomi": ["Lombardia"],
                "province_nomi": ["Milano"],
                "comuni_nomi": ["Milano", "Monza"],
                "municipi": [1, 2, 3],
                "territorio": "Province: Milano | Comuni: Milano, Monza | Roma - Municipi: 1, 2, 3",
                "delegato_nome": "Rossi Mario",
                "delegato_carica": "Deputato",
                "n_designazioni": 15,
                "n_bozze": 2
            }
        }

        # Schema per template DESIGNATION (Designazione RDL)
        # Struttura: per ogni sezione, una riga con effettivo E supplente
        designation_schema = {
            "delegato": {
                "id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "luogo_nascita": "Roma",
                "data_nascita": "1980-01-15",
                "carica": "DEPUTATO",
                "carica_display": "Deputato",
                "circoscrizione": "Lazio 1",
                "data_nomina": "2024-01-01",
                "email": "mario.rossi@m5s.it",
                "telefono": "+39 123456789",
                "territorio": "Regioni: Lazio",
                "n_sub_deleghe": 5
            },
            "subdelegato": {
                "id": 10,
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "email": "anna.bianchi@example.com",
                "telefono": "+39 987654321",
                "territorio": "Province: Milano | Comuni: Milano, Monza",
                "delegato_nome": "Rossi Mario",
                "tipo_delega_display": "Firma Autenticata"
            },
            "designazioni": [
                {
                    "sezione_id": 1,
                    "sezione_numero": "001",
                    "sezione_comune": "Milano",
                    "sezione_indirizzo": "Via Roma 1, 20121 Milano",
                    "sezione_municipio": 1,
                    "effettivo_id": 100,
                    "effettivo_cognome": "Verdi",
                    "effettivo_nome": "Luigi",
                    "effettivo_nome_completo": "Verdi Luigi",
                    "effettivo_luogo_nascita": "Torino",
                    "effettivo_data_nascita": "1990-03-20",
                    "effettivo_domicilio": "Via Milano 5, 20122 Milano (MI)",
                    "effettivo_email": "luigi.verdi@example.com",
                    "effettivo_telefono": "+39 111222333",
                    "effettivo_data_designazione": "2024-03-15",
                    "effettivo_stato": "CONFERMATA",
                    "effettivo_stato_display": "Confermata",
                    "supplente_id": 101,
                    "supplente_cognome": "Gialli",
                    "supplente_nome": "Maria",
                    "supplente_nome_completo": "Gialli Maria",
                    "supplente_luogo_nascita": "Bologna",
                    "supplente_data_nascita": "1988-07-10",
                    "supplente_domicilio": "Via Torino 8, 20123 Milano (MI)",
                    "supplente_email": "maria.gialli@example.com",
                    "supplente_telefono": "+39 444555666",
                    "supplente_data_designazione": "2024-03-15",
                    "supplente_stato": "CONFERMATA",
                    "supplente_stato_display": "Confermata"
                },
                {
                    "sezione_id": 2,
                    "sezione_numero": "002",
                    "sezione_comune": "Milano",
                    "sezione_indirizzo": "Via Milano 10, 20122 Milano",
                    "sezione_municipio": 1,
                    "effettivo_id": 102,
                    "effettivo_cognome": "Neri",
                    "effettivo_nome": "Paolo",
                    "effettivo_nome_completo": "Neri Paolo",
                    "effettivo_luogo_nascita": "Napoli",
                    "effettivo_data_nascita": "1992-11-05",
                    "effettivo_domicilio": "Via Napoli 12, 20124 Milano (MI)",
                    "effettivo_email": "paolo.neri@example.com",
                    "effettivo_telefono": "+39 777888999",
                    "effettivo_data_designazione": "2024-03-15",
                    "effettivo_stato": "CONFERMATA",
                    "effettivo_stato_display": "Confermata",
                    "supplente_id": 103,
                    "supplente_cognome": "Blu",
                    "supplente_nome": "Carla",
                    "supplente_nome_completo": "Blu Carla",
                    "supplente_luogo_nascita": "Firenze",
                    "supplente_data_nascita": "1995-02-28",
                    "supplente_domicilio": "Via Firenze 3, 20125 Milano (MI)",
                    "supplente_email": "carla.blu@example.com",
                    "supplente_telefono": "+39 333444555",
                    "supplente_data_designazione": "2024-03-16",
                    "supplente_stato": "BOZZA",
                    "supplente_stato_display": "Bozza"
                },
                {
                    "sezione_id": 3,
                    "sezione_numero": "003",
                    "sezione_comune": "Milano",
                    "sezione_indirizzo": "Via Dante 15, 20123 Milano",
                    "sezione_municipio": 2,
                    "effettivo_id": 104,
                    "effettivo_cognome": "Rossi",
                    "effettivo_nome": "Luca",
                    "effettivo_nome_completo": "Rossi Luca",
                    "effettivo_luogo_nascita": "Genova",
                    "effettivo_data_nascita": "1987-05-12",
                    "effettivo_domicilio": "Via Genova 20, 20126 Milano (MI)",
                    "effettivo_email": "luca.rossi@example.com",
                    "effettivo_telefono": "+39 222333444",
                    "effettivo_data_designazione": "2024-03-15",
                    "effettivo_stato": "CONFERMATA",
                    "effettivo_stato_display": "Confermata",
                    "supplente_id": "",
                    "supplente_cognome": "",
                    "supplente_nome": "",
                    "supplente_nome_completo": "",
                    "supplente_luogo_nascita": "",
                    "supplente_data_nascita": "",
                    "supplente_domicilio": "",
                    "supplente_email": "",
                    "supplente_telefono": "",
                    "supplente_data_designazione": "",
                    "supplente_stato": "",
                    "supplente_stato_display": ""
                }
            ]
        }

        # Update DELEGATION templates
        delegation_templates = Template.objects.filter(template_type='DELEGATION')
        delegation_count = delegation_templates.update(variables_schema=delegation_schema)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Aggiornati {delegation_count} template DELEGATION')
        )

        # Schema per template DESIGNATION SINGOLA (senza loop)
        # Una sola designazione per documento (più semplice)
        designation_single_schema = {
            "delegato": {
                "id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "nome_completo": "Rossi Mario",
                "luogo_nascita": "Roma",
                "data_nascita": "1980-01-15",
                "carica": "DEPUTATO",
                "carica_display": "Deputato",
                "circoscrizione": "Lazio 1",
                "data_nomina": "2024-01-01",
                "email": "mario.rossi@m5s.it",
                "telefono": "+39 123456789",
                "territorio": "Regioni: Lazio",
                "n_sub_deleghe": 5
            },
            "subdelegato": {
                "id": 10,
                "cognome": "Bianchi",
                "nome": "Anna",
                "nome_completo": "Bianchi Anna",
                "email": "anna.bianchi@example.com",
                "telefono": "+39 987654321",
                "territorio": "Province: Milano | Comuni: Milano, Monza",
                "delegato_nome": "Rossi Mario",
                "tipo_delega_display": "Firma Autenticata"
            },
            "designazione": {
                "sezione_id": 1,
                "sezione_numero": "001",
                "sezione_comune": "Milano",
                "sezione_indirizzo": "Via Roma 1, 20121 Milano",
                "sezione_municipio": 1,
                "effettivo_id": 100,
                "effettivo_cognome": "Verdi",
                "effettivo_nome": "Luigi",
                "effettivo_nome_completo": "Verdi Luigi",
                "effettivo_luogo_nascita": "Torino",
                "effettivo_data_nascita": "1990-03-20",
                "effettivo_domicilio": "Via Milano 5, 20122 Milano (MI)",
                "effettivo_email": "luigi.verdi@example.com",
                "effettivo_telefono": "+39 111222333",
                "effettivo_data_designazione": "2024-03-15",
                "effettivo_stato": "CONFERMATA",
                "effettivo_stato_display": "Confermata",
                "supplente_id": 101,
                "supplente_cognome": "Gialli",
                "supplente_nome": "Maria",
                "supplente_nome_completo": "Gialli Maria",
                "supplente_luogo_nascita": "Bologna",
                "supplente_data_nascita": "1988-07-10",
                "supplente_domicilio": "Via Torino 8, 20123 Milano (MI)",
                "supplente_email": "maria.gialli@example.com",
                "supplente_telefono": "+39 444555666",
                "supplente_data_designazione": "2024-03-15",
                "supplente_stato": "CONFERMATA",
                "supplente_stato_display": "Confermata"
            }
        }

        # Update DESIGNATION templates (multipla con loop)
        designation_templates = Template.objects.filter(
            template_type='DESIGNATION',
            name__icontains='individuale'
        )
        designation_count = designation_templates.update(variables_schema=designation_schema)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Aggiornati {designation_count} template DESIGNATION (multipla)')
        )

        # Update DESIGNATION SINGLE templates (senza loop)
        designation_single_templates = Template.objects.filter(
            template_type='DESIGNATION',
            name__icontains='singola'
        )
        designation_single_count = designation_single_templates.update(variables_schema=designation_single_schema)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Aggiornati {designation_single_count} template DESIGNATION (singola)')
        )

        total = delegation_count + designation_count + designation_single_count
        if total == 0:
            self.stdout.write(
                self.style.WARNING('⚠ Nessun template trovato da aggiornare')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Totale: {total} template aggiornati con successo!')
            )
            self.stdout.write('\nPer vedere i campi disponibili:')
            self.stdout.write('  - DELEGATION: $.delegato.*, $.subdelegato.*')
            self.stdout.write('  - DESIGNATION (multipla): $.delegato.*, $.subdelegato.*, $.designazioni[].*')
            self.stdout.write('                            (ogni elemento ha effettivo_* e supplente_* per la stessa sezione)')
            self.stdout.write('  - DESIGNATION (singola): $.delegato.*, $.subdelegato.*, $.designazione.*')
            self.stdout.write('                           (un oggetto con effettivo_* e supplente_*, senza loop)')
