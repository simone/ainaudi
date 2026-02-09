"""
Management command to load Roma delegates for Referendum 2026 and assign territory.

Usage:
    python manage.py load_delegati_roma
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from territory.models import Comune
from elections.models import ConsultazioneElettorale
from delegations.models import Delegato
from core.models import RoleAssignment


class Command(BaseCommand):
    help = 'Load Roma delegates for Referendum 2026 and assign territory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('Loading Roma delegates for Referendum 2026...')
        self.stdout.write('')

        # Get references
        try:
            consultazione = ConsultazioneElettorale.objects.get(nome__icontains='2026')
            comune_roma = Comune.objects.get(codice_istat='058091')
        except Exception as e:
            self.stderr.write(f'Error getting references: {e}')
            self.stderr.write('Make sure Referendum 2026 and Roma are in the database.')
            return

        self.stdout.write(f'Consultazione: {consultazione.nome}')
        self.stdout.write(f'Territorio: {comune_roma.nome} ({comune_roma.provincia.nome})')
        self.stdout.write('')

        # Delegati data
        delegati_data = [
            {
                'cognome': 'Pietracci',
                'nome': 'Daniela',
                'email': 'danielapietracci@gmail.com',
            },
            {
                'cognome': 'Federici',
                'nome': 'Simone',
                'email': 's.federici@gmail.com',
            },
            {
                'cognome': 'Meleo',
                'nome': 'Linda',
                'email': 'linda.meleo@movimento5stelle.eu',
            },
            {
                'cognome': 'Contardi',
                'nome': 'Federica',
                'email': 'efsi2365@gmail.com',
            },
            {
                'cognome': 'Riccardi',
                'nome': 'Marina',
                'email': 'marinariccardi961@gmail.com',
            },
        ]

        created_count = 0
        updated_count = 0

        if dry_run:
            # Dry run: check what would be created
            for data in delegati_data:
                cognome = data['cognome']
                nome = data['nome']
                email = data['email']

                exists = Delegato.objects.filter(
                    consultazione=consultazione,
                    cognome=cognome,
                    nome=nome
                ).exists()

                if exists:
                    self.stdout.write(f'  ⏭️  Already exists: {nome} {cognome}')
                else:
                    self.stdout.write(f'  ✨ Would create: {nome} {cognome} ({email})')
                    created_count += 1
        else:
            # Real execution
            with transaction.atomic():
                for data in delegati_data:
                    cognome = data['cognome']
                    nome = data['nome']
                    email = data['email']

                    # Check if already exists
                    delegato, created = Delegato.objects.get_or_create(
                        consultazione=consultazione,
                        cognome=cognome,
                        nome=nome,
                        defaults={
                            'email': email,
                            'carica': 'RAPPRESENTANTE_PARTITO',
                        }
                    )

                    if created:
                        # Assign territory: ONLY comune Roma (not regione/provincia)
                        delegato.comuni.add(comune_roma)
                        self.stdout.write(f'  ✅ Created: {nome} {cognome} ({email})')
                        created_count += 1

                        # Update RoleAssignment to be scoped to comune (not global)
                        # The signal creates a GLOBAL role, we need to fix it
                        user = delegato.user
                        if user:
                            RoleAssignment.objects.filter(
                                user=user,
                                role=RoleAssignment.Role.DELEGATE,
                                scope_type=RoleAssignment.ScopeType.GLOBAL
                            ).update(
                                scope_type=RoleAssignment.ScopeType.COMUNE,
                                scope_value=comune_roma.nome,
                                scope_comune=comune_roma,
                                consultazione=consultazione
                            )
                            self.stdout.write(f'     → Role scoped to comune: {comune_roma.nome}')
                    else:
                        # Update email if changed
                        if delegato.email != email:
                            delegato.email = email
                            delegato.save()
                            updated_count += 1
                            self.stdout.write(f'  🔄 Updated email: {nome} {cognome}')
                        else:
                            self.stdout.write(f'  ⏭️  Already exists: {nome} {cognome}')

                        # Ensure territory is set (only comune)
                        if comune_roma not in delegato.comuni.all():
                            delegato.comuni.add(comune_roma)
                            self.stdout.write(f'     → Territory added: {comune_roma.nome}')

                        # Ensure role is scoped correctly
                        user = delegato.user
                        if user:
                            role_assignment = RoleAssignment.objects.filter(
                                user=user,
                                role=RoleAssignment.Role.DELEGATE
                            ).first()

                            if role_assignment and role_assignment.scope_type == RoleAssignment.ScopeType.GLOBAL:
                                role_assignment.scope_type = RoleAssignment.ScopeType.COMUNE
                                role_assignment.scope_value = comune_roma.nome
                                role_assignment.scope_comune = comune_roma
                                role_assignment.consultazione = consultazione
                                role_assignment.save()
                                self.stdout.write(f'     → Role fixed: now scoped to {comune_roma.nome}')

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'DRY RUN - would create {created_count} delegates'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} delegates, updated {updated_count}'))
            self.stdout.write('')
            self.stdout.write('Territory assigned:')
            self.stdout.write(f'  • Comune: {comune_roma.nome}')
            self.stdout.write(f'  • Role scope: COMUNE (not global)')
