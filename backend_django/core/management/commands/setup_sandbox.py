"""
Setup ambiente Sandbox per test designazioni, scrutinio, dashboard e AI.

Crea:
- Regione/Provincia/Comuni/Sezioni fittizi (Topolinia + Paperopoli)
- Gruppo "Tester" con permessi: Dashboard, Scrutinio, Risorse, AI Chat

Idempotente: può essere eseguito più volte senza creare duplicati.

Usage:
    python manage.py setup_sandbox
    python manage.py setup_sandbox --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from territory.models import Regione, Provincia, Comune, SezioneElettorale


SEZIONI_TOPOLINIA = [
    (1, 'Scuola Pippo', 'Via dei Topi 1'),
    (2, 'Scuola Minnie', 'Via dei Fiori 3'),
    (3, 'Scuola Pluto', 'Via del Parco 7'),
    (4, 'Scuola Paperino', 'Via delle Querce 12'),
    (5, 'Scuola Paperone', "Via dell'Oro 99"),
]

SEZIONI_PAPEROPOLI = [
    (1, 'Scuola Archimede', 'Via degli Inventori 1'),
    (2, 'Scuola Gastone', 'Via della Fortuna 13'),
    (3, 'Scuola Qui Quo Qua', 'Via dei Nipoti 3'),
    (4, 'Scuola Nonna Papera', 'Via della Fattoria 5'),
    (5, 'Scuola Rockerduck', 'Via del Business 42'),
]

TESTER_PERMISSIONS = [
    'can_view_dashboard',
    'has_scrutinio_access',
    'can_view_resources',
    'can_ask_to_ai_assistant',
]


class Command(BaseCommand):
    help = 'Setup ambiente Sandbox: territorio fittizio + gruppo Tester'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe creato senza farlo',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - nessuna modifica applicata\n'))

        with transaction.atomic():
            self._create_territory(dry_run)
            self._create_tester_group(dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS('\nSetup Sandbox completato.'))

    def _create_territory(self, dry_run):
        self.stdout.write('\n--- Territorio ---')

        # Regione
        regione, created = Regione.objects.update_or_create(
            codice_istat='99',
            defaults={'nome': 'Sandbox'}
        )
        self._log('Regione', 'Sandbox', created)

        # Provincia
        provincia, created = Provincia.objects.update_or_create(
            codice_istat='999',
            defaults={
                'nome': 'Sandbox',
                'sigla': 'SB',
                'regione': regione,
            }
        )
        self._log('Provincia', 'Sandbox (SB)', created)

        # Comune Topolinia
        topolinia, created = Comune.objects.update_or_create(
            codice_istat='999001',
            defaults={
                'nome': 'Topolinia',
                'codice_catastale': 'Z001',
                'provincia': provincia,
            }
        )
        self._log('Comune', 'Topolinia', created)

        for numero, denominazione, indirizzo in SEZIONI_TOPOLINIA:
            sez, created = SezioneElettorale.objects.update_or_create(
                comune=topolinia,
                numero=numero,
                defaults={
                    'denominazione': denominazione,
                    'indirizzo': indirizzo,
                    'is_attiva': True,
                }
            )
            self._log('  Sezione', f'{numero} - {denominazione}', created)

        # Comune Paperopoli
        paperopoli, created = Comune.objects.update_or_create(
            codice_istat='999002',
            defaults={
                'nome': 'Paperopoli',
                'codice_catastale': 'Z002',
                'provincia': provincia,
            }
        )
        self._log('Comune', 'Paperopoli', created)

        for numero, denominazione, indirizzo in SEZIONI_PAPEROPOLI:
            sez, created = SezioneElettorale.objects.update_or_create(
                comune=paperopoli,
                numero=numero,
                defaults={
                    'denominazione': denominazione,
                    'indirizzo': indirizzo,
                    'is_attiva': True,
                }
            )
            self._log('  Sezione', f'{numero} - {denominazione}', created)

    def _create_tester_group(self, dry_run):
        self.stdout.write('\n--- Gruppo Tester ---')

        group, created = Group.objects.get_or_create(name='Tester')
        self._log('Gruppo', 'Tester', created)

        # Trova i permessi custom
        try:
            ct = ContentType.objects.get(app_label='core', model='custompermission')
        except ContentType.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'ContentType core.custompermission non trovato. Esegui le migrazioni.'
            ))
            return

        perms = Permission.objects.filter(codename__in=TESTER_PERMISSIONS, content_type=ct)

        found = set(perms.values_list('codename', flat=True))
        missing = set(TESTER_PERMISSIONS) - found
        if missing:
            self.stdout.write(self.style.WARNING(f'  Permessi non trovati: {missing}'))

        group.permissions.set(perms)
        for p in perms:
            self.stdout.write(f'  + {p.codename}')

        self.stdout.write(self.style.SUCCESS(f'  {perms.count()} permessi assegnati al gruppo Tester'))

    def _log(self, entity, name, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f'  + {entity}: {name}'))
        else:
            self.stdout.write(f'  = {entity}: {name} (esistente)')
