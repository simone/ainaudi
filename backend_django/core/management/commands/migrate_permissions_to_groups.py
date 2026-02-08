"""
Management command per migrare i permessi diretti degli utenti ai gruppi.

Questo comando:
1. Trova tutti gli utenti con RoleAssignment
2. Assegna il gruppo appropriato in base al ruolo
3. Rimuove i permessi diretti (ora ereditati dal gruppo)
4. Genera report delle modifiche

Usage:
    python manage.py migrate_permissions_to_groups
    python manage.py migrate_permissions_to_groups --dry-run
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction

from core.models import User, RoleAssignment


class Command(BaseCommand):
    help = 'Migra i permessi diretti degli utenti ai gruppi Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza applicare modifiche',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be applied\n'))

        # Mapping ruolo → gruppo
        role_to_group = {
            RoleAssignment.Role.DELEGATE: 'Delegato',
            RoleAssignment.Role.SUBDELEGATE: 'Subdelegato',
            RoleAssignment.Role.RDL: 'RDL',
            RoleAssignment.Role.KPI_VIEWER: 'Diretta',
        }

        # Verifica che i gruppi esistano
        missing_groups = []
        for group_name in role_to_group.values():
            if not Group.objects.filter(name=group_name).exists():
                missing_groups.append(group_name)

        if missing_groups:
            self.stdout.write(
                self.style.ERROR(
                    f'ERROR: Missing groups: {", ".join(missing_groups)}\n'
                    f'Run migrations first: python manage.py migrate'
                )
            )
            return

        # Trova tutti gli utenti con RoleAssignment
        role_assignments = RoleAssignment.objects.select_related('user').filter(is_active=True)

        self.stdout.write(f'Found {role_assignments.count()} active role assignments\n')

        users_migrated = 0
        permissions_removed = 0
        groups_assigned = 0

        with transaction.atomic():
            for assignment in role_assignments:
                user = assignment.user
                role = assignment.role

                # Skip superusers
                if user.is_superuser:
                    continue

                group_name = role_to_group.get(role)
                if not group_name:
                    self.stdout.write(
                        self.style.WARNING(f'  No group mapping for role {role} (user: {user.email})')
                    )
                    continue

                # Get group
                group = Group.objects.get(name=group_name)

                # Add user to group
                if group not in user.groups.all():
                    if not dry_run:
                        user.groups.add(group)
                    groups_assigned += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {user.email} → group {group_name}')
                    )
                else:
                    self.stdout.write(f'  - {user.email} already in group {group_name}')

                # Remove direct permissions (now inherited from group)
                direct_perms = user.user_permissions.all()
                if direct_perms.exists():
                    perm_count = direct_perms.count()
                    if not dry_run:
                        user.user_permissions.clear()
                    permissions_removed += perm_count
                    self.stdout.write(
                        self.style.WARNING(f'    Removed {perm_count} direct permissions')
                    )

                users_migrated += 1

            if dry_run:
                self.stdout.write(self.style.WARNING('\nDRY RUN - Rolling back transaction\n'))
                transaction.set_rollback(True)

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'Migration {"would be" if dry_run else "completed"}:'))
        self.stdout.write(f'  - Users migrated: {users_migrated}')
        self.stdout.write(f'  - Groups assigned: {groups_assigned}')
        self.stdout.write(f'  - Direct permissions removed: {permissions_removed}')
        self.stdout.write('='*60 + '\n')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('Run without --dry-run to apply changes')
            )
