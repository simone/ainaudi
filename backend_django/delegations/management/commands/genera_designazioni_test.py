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

        # Get sections that already have active CONFERMATA designations
        # We'll deactivate these and replace them with test designations
        designazioni_esistenti = DesignazioneRDL.objects.filter(
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
            if count_skipped > 0:
                msg += f'Will deactivate {count_skipped} existing CONFERMATA designations'
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

        # Build designations from assignments
        count_created = 0
        designazioni_to_create = []

        for assignment in assignments:
            rdl_reg = assignment.rdl_registration

            # Determine email based on role
            if assignment.role == SectionAssignment.Role.RDL:
                effettivo_email = rdl_reg.email
                supplente_email = ''
            else:  # SUPPLENTE
                effettivo_email = ''
                supplente_email = rdl_reg.email

            designazione = DesignazioneRDL(
                processo=processo_test if not dry_run else None,
                delegato=delegato_test if not dry_run else None,  # Link to test delegato
                sezione=assignment.sezione,
                stato='CONFERMATA',
                is_attiva=True,
                # Effettivo data
                effettivo_email=effettivo_email,
                effettivo_nome=rdl_reg.nome,
                effettivo_cognome=rdl_reg.cognome,
                effettivo_telefono=rdl_reg.telefono,
                effettivo_data_nascita=rdl_reg.data_nascita,
                effettivo_luogo_nascita=rdl_reg.comune_nascita,
                effettivo_domicilio=rdl_reg.indirizzo_residenza,
                # Supplente data
                supplente_email=supplente_email,
                supplente_nome=rdl_reg.nome,
                supplente_cognome=rdl_reg.cognome,
                supplente_telefono=rdl_reg.telefono,
                supplente_data_nascita=rdl_reg.data_nascita,
                supplente_luogo_nascita=rdl_reg.comune_nascita,
                supplente_domicilio=rdl_reg.indirizzo_residenza,
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

        # Bulk create designations
        DesignazioneRDL.objects.bulk_create(designazioni_to_create)

        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {count_created} test designations')
        )
