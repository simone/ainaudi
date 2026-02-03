"""
Management command to identify and optionally clean up unused/test accounts.

Usage:
    # List unused accounts (dry run)
    python manage.py cleanup_users

    # Actually delete unused accounts
    python manage.py cleanup_users --delete

    # Include superusers in the scan (careful!)
    python manage.py cleanup_users --include-superusers

Criteria for "unused" accounts:
- No login in the last 90 days (configurable via --days)
- No associated domain entities (delegato, subdelega, designazione, registration)
- Not a superuser (unless --include-superusers)
- Not staff
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from core.models import User, RoleAssignment


class Command(BaseCommand):
    help = 'Identify and clean up unused/test user accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Actually delete unused accounts (default is dry run)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days since last login to consider unused (default: 90)',
        )
        parser.add_argument(
            '--include-superusers',
            action='store_true',
            help='Include superusers in the scan (use with caution)',
        )
        parser.add_argument(
            '--email-pattern',
            type=str,
            help='Only check users matching this email pattern (e.g., "@test.com")',
        )

    def handle(self, *args, **options):
        delete = options['delete']
        days = options['days']
        include_superusers = options['include_superusers']
        email_pattern = options.get('email_pattern')

        threshold_date = timezone.now() - timedelta(days=days)

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"User Cleanup {'(DRY RUN)' if not delete else '⚠️  DELETING'}\n"
            f"{'='*60}\n"
            f"Threshold: {days} days (no login since {threshold_date.date()})\n"
        ))

        # Build base queryset
        users = User.objects.all()

        # Exclude superusers unless explicitly included
        if not include_superusers:
            users = users.exclude(is_superuser=True)

        # Exclude staff
        users = users.exclude(is_staff=True)

        # Filter by email pattern if specified
        if email_pattern:
            users = users.filter(email__icontains=email_pattern)

        # Find users with no recent login
        users_no_login = users.filter(
            Q(last_login__isnull=True) | Q(last_login__lt=threshold_date)
        )

        self.stdout.write(f"\nTotal users (excluding staff/superuser): {users.count()}")
        self.stdout.write(f"Users with no recent login: {users_no_login.count()}")

        # Check for domain entity links
        unused_users = []
        linked_users = []

        for user in users_no_login:
            has_links = self._has_domain_links(user)

            if has_links:
                linked_users.append(user)
            else:
                unused_users.append(user)

        self.stdout.write(f"\n--- Users with domain links (KEEP): {len(linked_users)} ---")
        for user in linked_users[:10]:  # Show first 10
            self.stdout.write(f"  ✓ {user.email} - linked to domain entities")
        if len(linked_users) > 10:
            self.stdout.write(f"  ... and {len(linked_users) - 10} more")

        self.stdout.write(f"\n--- Unused users (candidates for deletion): {len(unused_users)} ---")
        for user in unused_users:
            self.stdout.write(f"  ✗ {user.email}")
            self.stdout.write(f"      Created: {user.created_at.date() if user.created_at else 'N/A'}")
            self.stdout.write(f"      Last login: {user.last_login.date() if user.last_login else 'Never'}")

        if not unused_users:
            self.stdout.write(self.style.SUCCESS("\n✓ No unused accounts found!"))
            return

        # Delete if requested
        if delete:
            self.stdout.write(self.style.WARNING(f"\n⚠️  About to delete {len(unused_users)} users..."))
            confirm = input("Type 'DELETE' to confirm: ")

            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR("Aborted."))
                return

            deleted_count = 0
            for user in unused_users:
                email = user.email
                try:
                    user.delete()
                    deleted_count += 1
                    self.stdout.write(f"  Deleted: {email}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Failed to delete {email}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"\n✓ Deleted {deleted_count} users"))
        else:
            self.stdout.write(self.style.NOTICE(
                f"\n👆 Run with --delete to actually delete these {len(unused_users)} users"
            ))

    def _has_domain_links(self, user):
        """Check if user has any links to domain entities."""
        from delegations.models import DelegatoDiLista, SubDelega, DesignazioneRDL
        from campaign.models import RdlRegistration
        from data.models import SectionAssignment

        # Check delegation chain
        if DelegatoDiLista.objects.filter(email=user.email).exists():
            return True

        if SubDelega.objects.filter(email=user.email).exists():
            return True

        if DesignazioneRDL.objects.filter(email=user.email).exists():
            return True

        # Check RDL registrations
        if RdlRegistration.objects.filter(email=user.email).exists():
            return True

        # Check section assignments
        if SectionAssignment.objects.filter(rdl_registration__email=user.email).exists():
            return True

        # Check role assignments
        if RoleAssignment.objects.filter(user=user, is_active=True).exists():
            return True

        return False
