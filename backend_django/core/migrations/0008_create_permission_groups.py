# Generated migration for permission groups

from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def create_permission_groups(apps, schema_editor):
    """
    Crea i 4 gruppi di permessi e assegna i permessi custom a ciascun gruppo.

    Gruppi:
    - Delegato: accesso completo a deleghe, RDL, risorse, documenti, KPI
    - Subdelegato: gestione RDL, risorse, KPI (limitato)
    - RDL: solo scrutinio e risorse
    - Diretta: accesso KPI e risorse (viewer role)
    """
    # Get content type for CustomPermission
    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
    except ContentType.DoesNotExist:
        print("WARNING: CustomPermission content type not found. Run migrations first.")
        return

    # Define groups and their permissions
    groups_permissions = {
        'Delegato': [
            'can_manage_delegations',
            'can_manage_rdl',
            'can_view_resources',
            'can_generate_documents',
            'can_view_kpi',
        ],
        'Subdelegato': [
            'can_manage_rdl',
            'can_view_resources',
            'can_view_kpi',
        ],
        'RDL': [
            'has_scrutinio_access',
            'can_view_resources',
        ],
        'Diretta': [
            'can_view_kpi',
            'can_view_resources',
        ],
    }

    for group_name, permission_codenames in groups_permissions.items():
        # Create or get group
        group, created = Group.objects.get_or_create(name=group_name)

        if created:
            print(f"Created group: {group_name}")
        else:
            print(f"Group already exists: {group_name}")
            # Clear existing permissions to ensure clean state
            group.permissions.clear()

        # Get permissions by codename
        permissions = Permission.objects.filter(
            codename__in=permission_codenames,
            content_type=content_type
        )

        # Assign permissions to group
        group.permissions.set(permissions)
        print(f"  Assigned {permissions.count()} permissions to {group_name}")


def remove_permission_groups(apps, schema_editor):
    """Remove the created groups on migration rollback."""
    Group.objects.filter(name__in=['Delegato', 'Subdelegato', 'RDL', 'Diretta']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_custompermission'),
    ]

    operations = [
        migrations.RunPython(create_permission_groups, remove_permission_groups),
    ]
