"""
Management command to delete users that are NOT delegates and NOT approved RDLs.

Usage:
    python manage.py cleanup_non_delegated_users --dry-run  # Preview what will be deleted
    python manage.py cleanup_non_delegated_users             # Actually delete

Criteria for deletion:
- NOT a superuser
- NOT a staff user
- NOT a DELEGATE
- NOT an RDL with APPROVED RdlRegistration

This is useful for cleaning up test/spam accounts.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import User, RoleAssignment
from campaign.models import RdlRegistration


class Command(BaseCommand):
    help = 'Delete users that are not delegates or approved RDLs (preserves superusers)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting (default)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete (without --confirm, only dry-run)',
        )

    def handle(self, *args, **options):
        dry_run = not options.get('confirm', False)

        # Find users to KEEP:
        # 1. Superusers
        # 2. Staff users
        # 3. Users with DELEGATE role
        # 4. Users with APPROVED RdlRegistration

        superusers = User.objects.filter(is_superuser=True).distinct()
        staff_users = User.objects.filter(is_staff=True).distinct()
        delegates = User.objects.filter(role_assignments__role='DELEGATE').distinct()

        # Approved RDL registrations
        approved_rdl_emails = RdlRegistration.objects.filter(
            status='APPROVED'
        ).values_list('email', flat=True)
        approved_rdl_users = User.objects.filter(email__in=approved_rdl_emails).distinct()

        # Combine all users to keep
        users_to_keep = (
            superusers | staff_users | delegates | approved_rdl_users
        ).distinct()

        # Find users to delete (all except those we keep)
        users_to_delete = User.objects.exclude(id__in=users_to_keep).order_by('email')

        count = users_to_delete.count()

        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING(f'User Cleanup Report'))
        self.stdout.write(self.style.WARNING('='*70))

        self.stdout.write('')
        self.stdout.write(f'Total users in system: {User.objects.count()}')
        self.stdout.write(f'Superusers (protected): {superusers.count()}')
        self.stdout.write(f'Staff users (protected): {staff_users.count()}')
        self.stdout.write(f'Delegates (protected): {delegates.count()}')
        self.stdout.write(f'Approved RDLs (protected): {approved_rdl_users.count()}')
        self.stdout.write('')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No users to delete - all users are protected'))
            return

        self.stdout.write(self.style.ERROR(f'❌ Users to DELETE: {count}'))
        self.stdout.write('')

        if count > 0:
            self.stdout.write('Deletion candidates:')
            for user in users_to_delete:
                role_count = user.role_assignments.count()
                rdl_count = RdlRegistration.objects.filter(email=user.email).count()
                self.stdout.write(
                    f'  • {user.email}\n'
                    f'    Created: {user.created_at.date() if user.created_at else "N/A"}, '
                    f'Last login: {user.last_login.date() if user.last_login else "Never"}, '
                    f'Roles: {role_count}, RDL registrations: {rdl_count}'
                )

        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'🔍 DRY RUN MODE: Would delete {count} users\n'
                f'   Run with --confirm to actually delete'
            ))
        else:
            self.stdout.write(self.style.ERROR(f'⚠️  ACTUALLY DELETING {count} users...'))
            self.stdout.write(self.style.ERROR('   This action cannot be undone!'))
            self.stdout.write('')

            confirm = input('Type "DELETE" to confirm deletion: ')

            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR('❌ Aborted - no changes made'))
                return

            deleted_count, _ = users_to_delete.delete()
            self.stdout.write(self.style.SUCCESS(f'✅ Deleted {deleted_count} users'))
