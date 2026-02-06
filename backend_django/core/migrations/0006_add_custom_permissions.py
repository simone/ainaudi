# Generated manually - Custom permissions for granular access control

from django.db import migrations


def create_permissions(apps, schema_editor):
    """
    Crea permessi custom per il sistema.
    Usa django.contrib.auth.Permission esistente.
    """
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    # Get or create content type per "core" app e CustomPermission model
    content_type, _ = ContentType.objects.get_or_create(
        app_label='core',
        model='custompermission'
    )

    permissions = [
        ('can_manage_territory', 'Can manage territory (regions, provinces, comuni, sections)'),
        ('can_view_kpi', 'Can view KPI dashboard'),
        ('can_manage_elections', 'Can manage elections and ballots'),
        ('can_manage_delegations', 'Can manage delegations chain'),
        ('can_manage_rdl', 'Can manage RDL registrations'),
        ('has_scrutinio_access', 'Can enter section scrutinio data'),
        ('can_view_resources', 'Can view resources and documents'),
        ('can_ask_to_ai_assistant', 'Can use AI assistant chatbot'),
        ('can_generate_documents', 'Can generate PDF documents'),
        ('can_manage_incidents', 'Can manage incident reports'),
    ]

    for codename, name in permissions:
        Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={'name': name}
        )


def remove_permissions(apps, schema_editor):
    """Rimuove permessi custom (reverse migration)"""
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
        Permission.objects.filter(content_type=content_type).delete()
        content_type.delete()
    except ContentType.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_gruppo'),
        ('contenttypes', '__latest__'),
    ]

    operations = [
        migrations.RunPython(create_permissions, remove_permissions),
    ]
