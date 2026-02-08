# Migration to update permission groups with new granular permissions

from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def update_permission_groups(apps, schema_editor):
    """
    Aggiorna i 4 gruppi di permessi con i nuovi permessi granulari.
    Ogni voce del menu ha ora il suo permesso specifico.
    """
    # Get content type for CustomPermission
    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
    except ContentType.DoesNotExist:
        print("WARNING: CustomPermission content type not found.")
        return

    # Define groups and their permissions (completo per ogni voce menu)
    groups_permissions = {
        'Delegato': [
            # Ha accesso a tutto tranne scrutinio inserimento dati
            'can_view_dashboard',
            'can_manage_territory',          # Territorio
            'can_manage_elections',          # Consultazione
            'can_manage_campaign',           # Campagne
            'can_manage_rdl',                # Gestione RDL
            'can_manage_sections',           # Gestione Sezioni
            'can_manage_mappatura',          # Mappatura
            'can_manage_delegations',        # Catena Deleghe
            'can_manage_designazioni',       # Designazioni
            'can_manage_templates',          # Template PDF
            'can_generate_documents',        # Genera Moduli
            'can_view_resources',            # Risorse
            'can_view_live_results',         # Risultati Live
            'can_view_kpi',                  # Diretta
        ],
        'Subdelegato': [
            # Accesso limitato: non può gestire territorio, elezioni, deleghe
            'can_view_dashboard',
            'can_manage_campaign',           # Campagne
            'can_manage_rdl',                # Gestione RDL
            'can_manage_sections',           # Gestione Sezioni
            'can_manage_mappatura',          # Mappatura
            'can_manage_designazioni',       # Designazioni (se tipo=FIRMA_AUTENTICATA)
            'can_manage_templates',          # Template PDF
            'can_generate_documents',        # Genera Moduli
            'can_view_resources',            # Risorse
            'can_view_live_results',         # Risultati Live
            'can_view_kpi',                  # Diretta
        ],
        'RDL': [
            # Solo scrutinio e risorse
            'has_scrutinio_access',          # Scrutinio
            'can_view_resources',            # Risorse
        ],
        'Diretta': [
            # Solo visualizzazione KPI e risorse (viewer role)
            'can_view_kpi',                  # Diretta
            'can_view_resources',            # Risorse
        ],
    }

    for group_name, permission_codenames in groups_permissions.items():
        try:
            group = Group.objects.get(name=group_name)

            # Get permissions by codename
            permissions = Permission.objects.filter(
                codename__in=permission_codenames,
                content_type=content_type
            )

            # Clear and set new permissions
            group.permissions.clear()
            group.permissions.set(permissions)

            print(f"✓ Updated group {group_name} with {permissions.count()} permissions")

        except Group.DoesNotExist:
            print(f"⚠ Group {group_name} does not exist, skipping")


def reverse_permissions(apps, schema_editor):
    """Rollback: restore old permission set."""
    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
    except ContentType.DoesNotExist:
        return

    # Old permission structure (from 0008)
    old_groups_permissions = {
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

    for group_name, permission_codenames in old_groups_permissions.items():
        try:
            group = Group.objects.get(name=group_name)
            permissions = Permission.objects.filter(
                codename__in=permission_codenames,
                content_type=content_type
            )
            group.permissions.clear()
            group.permissions.set(permissions)
        except Group.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_update_permission_groups'),
    ]

    operations = [
        migrations.RunPython(update_permission_groups, reverse_permissions),
    ]
