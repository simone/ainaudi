"""
Management command to generate test designations based on SectionAssignments.

This allows RDLs to see sections during testing without going through the full
designation and approval workflow.

Usage:
    python manage.py genera_designazioni_test --consultazione-id 1
    python manage.py genera_designazioni_test --consultazione-id 1 --dry-run
    python manage.py genera_designazioni_test --consultazione-id 1 --delete
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from elections.models import ConsultazioneElettorale
from delegations.models import ProcessoDesignazione, DesignazioneRDL, Delegato
from data.models import SectionAssignment


class Command(BaseCommand):
    help = 'Generate test designations from SectionAssignments for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consultazione-id',
            type=int,
            required=True,
            help='ID of the consultazione to generate test data for'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all TEST designations and processes for this consultazione'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        consultazione_id = options['consultazione_id']
        dry_run = options['dry_run']
        delete = options['delete']

        try:
            consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
        except ConsultazioneElettorale.DoesNotExist:
            raise CommandError(f'ConsultazioneElettorale with ID {consultazione_id} not found')

        if delete:
            self._delete_test_data(consultazione, dry_run)
        else:
            self._generate_test_data(consultazione, dry_run)

    def _delete_test_data(self, consultazione, dry_run):
        """Delete all TEST designations, processes, and test delegato for the consultazione.

        Also reactivates any non-TEST designations that were deactivated during test setup.
        """
        processi_test = ProcessoDesignazione.objects.filter(
            consultazione=consultazione,
            stato=ProcessoDesignazione.Stato.TEST
        )

        if not processi_test.exists():
            self.stdout.write(
                self.style.WARNING('No TEST processes found for this consultazione')
            )
            return

        count_processi = processi_test.count()

        # Count designations to be deleted
        designazioni_test = DesignazioneRDL.objects.filter(
            processo__in=processi_test
        )
        count_designazioni = designazioni_test.count()

        # Find designations that were deactivated (not in TEST process, not active, not from test delegato)
        # These should be reactivated
        designazioni_da_riattivare = DesignazioneRDL.objects.filter(
            sezione__in=designazioni_test.values('sezione'),
            is_attiva=False,
            stato='CONFERMATA'
        ).exclude(processo__stato=ProcessoDesignazione.Stato.TEST)

        count_da_riattivare = designazioni_da_riattivare.count()

        # Check if test delegato exists (the one we created)
        delegato_test = Delegato.objects.filter(
            consultazione=consultazione,
            cognome='Designazioni',
            nome='Test'
        ).first()

        if dry_run:
            msg = f'DRY RUN: Would delete {count_designazioni} TEST designations across {count_processi} TEST processes'
            if count_da_riattivare > 0:
                msg += f' and reactivate {count_da_riattivare} original designations'
            if delegato_test:
                msg += f' and delete 1 test delegato'
            self.stdout.write(self.style.WARNING(msg))
            return

        # Delete test designations first
        designazioni_test.delete()
        processi_test.delete()

        # Reactivate original designations
        if count_da_riattivare > 0:
            designazioni_da_riattivare.update(is_attiva=True)
            self.stdout.write(
                self.style.WARNING(f'⚠ Reactivated {count_da_riattivare} original designations')
            )

        # Delete test delegato if it exists and no other designations reference it
        if delegato_test:
            if not DesignazioneRDL.objects.filter(delegato=delegato_test).exists():
                delegato_test.delete()

        self.stdout.write(
            self.style.SUCCESS(f'✓ Deleted {count_designazioni} test designations')
        )

    def _generate_test_data(self, consultazione, dry_run):
        """Generate test designations from SectionAssignments.

        Only creates designations for sections that don't already have an active
        CONFERMATA designation (respecting the unique constraint).
        """

        # Get all assignments for this consultazione
        assignments = SectionAssignment.objects.filter(
            consultazione=consultazione
        ).select_related('rdl_registration', 'sezione')

        if not assignments.exists():
            raise CommandError(
                f'No SectionAssignments found for consultazione {consultazione.nome}'
            )

        # Get sections (from current consultazione's assignments) that already have
        # active CONFERMATA designations. We'll deactivate these and replace them with test designations
        sezioni_assignment = set(assignments.values_list('sezione_id', flat=True))

        designazioni_esistenti = DesignazioneRDL.objects.filter(
            sezione_id__in=sezioni_assignment,
            is_attiva=True,
            stato='CONFERMATA'
        ).values_list('sezione_id', flat=True)
        sezioni_con_designazione = set(designazioni_esistenti)

        # Find or create a test delegato for this consultazione
        # Use the unique constraint (consultazione, cognome, nome)
        if not dry_run:
            delegato_test, created_delegato = Delegato.objects.get_or_create(
                consultazione=consultazione,
                cognome='Designazioni',
                nome='Test',
                defaults={
                    'carica': Delegato.Carica.RAPPRESENTANTE_PARTITO,
                    'email': 'test-designazioni@m5s.it',
                }
            )
            if created_delegato:
                self.stdout.write(
                    self.style.WARNING(f'Created test Delegato: {delegato_test.email}')
                )

        # Create a single TEST process for this consultazione
        if dry_run:
            msg = f'DRY RUN: Would create TEST process for consultazione: {consultazione.nome}\n'
            msg += f'Assignments found: {assignments.count()}\n'
            if sezioni_con_designazione:
                msg += f'Will deactivate {len(sezioni_con_designazione)} existing CONFERMATA designations'
            self.stdout.write(self.style.WARNING(msg))
        else:
            # Deactivate existing CONFERMATA designations that we'll replace
            if sezioni_con_designazione:
                deactivated_count = DesignazioneRDL.objects.filter(
                    sezione_id__in=sezioni_con_designazione,
                    is_attiva=True,
                    stato='CONFERMATA'
                ).update(is_attiva=False)
                if deactivated_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ Deactivated {deactivated_count} existing CONFERMATA designations'
                        )
                    )

            processo_test, created = ProcessoDesignazione.objects.get_or_create(
                consultazione=consultazione,
                stato=ProcessoDesignazione.Stato.TEST,
                defaults={
                    'tipo': ProcessoDesignazione.Tipo.INDIVIDUALE,
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created TEST process: {processo_test.id}')
                )

        # Group assignments by sezione (since there can be RDL + SUPPLENTE for same sezione)
        sezioni_map = {}  # sezione_id -> {'rdl': assignment, 'supplente': assignment}

        for assignment in assignments:
            sezione_id = assignment.sezione_id
            if sezione_id not in sezioni_map:
                sezioni_map[sezione_id] = {}

            if assignment.role == SectionAssignment.Role.RDL:
                sezioni_map[sezione_id]['rdl'] = assignment
            else:  # SUPPLENTE
                sezioni_map[sezione_id]['supplente'] = assignment

        # Build designations (one per sezione, collecting both RDL and SUPPLENTE)
        count_created = 0
        designazioni_to_create = []

        for sezione_id, roles_dict in sezioni_map.items():
            # Get sezione and data from assignments
            rdl_assignment = roles_dict.get('rdl')
            supplente_assignment = roles_dict.get('supplente')

            # Use whichever assignment exists (prefer RDL if both)
            assignment = rdl_assignment or supplente_assignment
            sezione = assignment.sezione

            # Collect effettivo data (from RDL assignment if exists, else supplente)
            effettivo_data = None
            effettivo_email = ''
            if rdl_assignment:
                effettivo_data = rdl_assignment.rdl_registration
                effettivo_email = effettivo_data.email

            # Collect supplente data (from SUPPLENTE assignment if exists)
            supplente_data = None
            supplente_email = ''
            if supplente_assignment:
                supplente_data = supplente_assignment.rdl_registration
                supplente_email = supplente_data.email

            # At least one email must exist (enforced by check constraint)
            if not effettivo_email and not supplente_email:
                continue

            # Use the first available RDL registration for data snapshot
            rdl_reg = effettivo_data or supplente_data

            designazione = DesignazioneRDL(
                processo=processo_test if not dry_run else None,
                delegato=delegato_test if not dry_run else None,  # Link to test delegato
                sezione=sezione,
                stato='CONFERMATA',
                is_attiva=True,
                # Effettivo data (if RDL role exists)
                effettivo_email=effettivo_email,
                effettivo_nome=effettivo_data.nome if effettivo_data else '',
                effettivo_cognome=effettivo_data.cognome if effettivo_data else '',
                effettivo_telefono=effettivo_data.telefono if effettivo_data else '',
                effettivo_data_nascita=effettivo_data.data_nascita if effettivo_data else None,
                effettivo_luogo_nascita=effettivo_data.comune_nascita if effettivo_data else '',
                effettivo_domicilio=effettivo_data.indirizzo_residenza if effettivo_data else '',
                # Supplente data (if SUPPLENTE role exists)
                supplente_email=supplente_email,
                supplente_nome=supplente_data.nome if supplente_data else '',
                supplente_cognome=supplente_data.cognome if supplente_data else '',
                supplente_telefono=supplente_data.telefono if supplente_data else '',
                supplente_data_nascita=supplente_data.data_nascita if supplente_data else None,
                supplente_luogo_nascita=supplente_data.comune_nascita if supplente_data else '',
                supplente_domicilio=supplente_data.indirizzo_residenza if supplente_data else '',
            )

            designazioni_to_create.append(designazione)
            count_created += 1

        if dry_run:
            msg = f'DRY RUN: Would create {count_created} test designations'
            if sezioni_con_designazione:
                msg += f'\n({len(sezioni_con_designazione)} will have existing designations deactivated)'
            self.stdout.write(self.style.WARNING(msg))
            return

        if count_created == 0:
            self.stdout.write(
                self.style.WARNING(f'ℹ No assignments found for {consultazione.nome}')
            )
            return

        # Bulk create designations (one per sezione, no duplicates)
        DesignazioneRDL.objects.bulk_create(designazioni_to_create)

        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {count_created} test designations')
        )
