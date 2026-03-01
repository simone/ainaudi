# Generated migration for syncing RDL approval status with user access

from django.db import migrations


def sync_rdl_approval_status(apps, schema_editor):
    """
    Sync existing RdlRegistration records with user access.

    For APPROVED RDLs:
    - Delete any non-comunal RoleAssignments (scope_type != 'comune')
    - Create RoleAssignment scoped to comune with consultazione
    - Add user to RDL group

    For REJECTED/PENDING RDLs:
    - Deactivate ALL RoleAssignment RDL
    - Remove user from RDL group
    """
    RdlRegistration = apps.get_model('campaign', 'RdlRegistration')
    RoleAssignment = apps.get_model('core', 'RoleAssignment')
    User = apps.get_model('core', 'User')
    Group = apps.get_model('auth', 'Group')

    # Get or create RDL group
    try:
        rdl_group = Group.objects.get(name='RDL')
    except Group.DoesNotExist:
        print("⚠️  RDL group not found - creating it")
        rdl_group = Group.objects.create(name='RDL')

    approved_count = 0
    revoked_count = 0
    deleted_count = 0

    # First pass: delete ALL non-comunal RDL assignments
    deleted_count = RoleAssignment.objects.filter(role='RDL').exclude(scope_type='comune').delete()[0]
    if deleted_count:
        print(f"🗑️  Deleted {deleted_count} non-comunal RDL assignments")

    # Process all RDL registrations
    for rdl in RdlRegistration.objects.select_related('comune', 'consultazione').all():
        try:
            user = User.objects.get(email=rdl.email.lower())
        except User.DoesNotExist:
            # User doesn't exist, skip
            continue

        if rdl.status == 'APPROVED':
            # Create correct RoleAssignment (scope_type='comune' with consultazione)
            role_assignment, created = RoleAssignment.objects.get_or_create(
                user=user,
                role='RDL',
                scope_type='comune',
                scope_comune=rdl.comune,
                consultazione=rdl.consultazione,
                defaults={
                    'assigned_by_email': rdl.approved_by_email or 'system@migration',
                    'is_active': True,
                }
            )

            # Activate if was deactivated
            if not role_assignment.is_active:
                role_assignment.is_active = True
                role_assignment.save()

            # Add user to RDL group
            user.groups.add(rdl_group)

            approved_count += 1

        else:
            # REJECTED or PENDING: deactivate all RDL assignments and remove from group
            RoleAssignment.objects.filter(
                user=user,
                role='RDL'
            ).update(is_active=False)

            user.groups.remove(rdl_group)

            revoked_count += 1

    print(f"✅ Synced RDL approval status:")
    print(f"  - {approved_count} APPROVED RDLs: access granted")
    print(f"  - {revoked_count} REJECTED/PENDING RDLs: access revoked")


def reverse_sync(apps, schema_editor):
    """
    Reverse migration: remove all RDL RoleAssignments and group memberships.
    This is destructive - only use for development/testing.
    """
    RoleAssignment = apps.get_model('core', 'RoleAssignment')
    Group = apps.get_model('auth', 'Group')

    try:
        rdl_group = Group.objects.get(name='RDL')
    except Group.DoesNotExist:
        return

    # Remove all RDL RoleAssignments
    count = RoleAssignment.objects.filter(role='RDL').delete()[0]

    # Remove all users from RDL group
    rdl_group.user_set.clear()

    print(f"⚠️  Reversed RDL sync: deleted {count} RoleAssignments")


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0009_fixture_invito_piattaforma'),
    ]

    operations = [
        migrations.RunPython(sync_rdl_approval_status, reverse_sync),
    ]
