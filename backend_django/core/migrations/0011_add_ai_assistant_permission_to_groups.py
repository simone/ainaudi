# Migration to add AI assistant permission to all user groups

from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def add_ai_assistant_permission(apps, schema_editor):
    """
    Aggiunge il permesso can_ask_to_ai_assistant a tutti i gruppi.
    L'AI assistant è una feature utile per tutti gli utenti autenticati.
    """
    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
    except ContentType.DoesNotExist:
        print("WARNING: CustomPermission content type not found.")
        return

    # Get the AI assistant permission
    try:
        ai_permission = Permission.objects.get(
            codename='can_ask_to_ai_assistant',
            content_type=content_type
        )
    except Permission.DoesNotExist:
        print("WARNING: can_ask_to_ai_assistant permission not found.")
        return

    # Add to all groups
    groups_to_update = ['Delegato', 'Subdelegato', 'RDL', 'Diretta']

    for group_name in groups_to_update:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.add(ai_permission)
            print(f"✓ Added AI assistant permission to {group_name}")
        except Group.DoesNotExist:
            print(f"⚠ Group {group_name} does not exist, skipping")


def remove_ai_assistant_permission(apps, schema_editor):
    """Rollback: remove AI assistant permission from groups."""
    try:
        content_type = ContentType.objects.get(
            app_label='core',
            model='custompermission'
        )
        ai_permission = Permission.objects.get(
            codename='can_ask_to_ai_assistant',
            content_type=content_type
        )
    except (ContentType.DoesNotExist, Permission.DoesNotExist):
        return

    groups_to_update = ['Delegato', 'Subdelegato', 'RDL', 'Diretta']

    for group_name in groups_to_update:
        try:
            group = Group.objects.get(name=group_name)
            group.permissions.remove(ai_permission)
        except Group.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_update_groups_with_new_permissions'),
    ]

    operations = [
        migrations.RunPython(add_ai_assistant_permission, remove_ai_assistant_permission),
    ]
