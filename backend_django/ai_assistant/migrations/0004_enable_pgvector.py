"""
Enable pgvector extension for vector similarity search.
"""
from django.db import connection, migrations


def enable_pgvector(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute('CREATE EXTENSION IF NOT EXISTS vector;')


def disable_pgvector(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute('DROP EXTENSION IF EXISTS vector;')


class Migration(migrations.Migration):
    dependencies = [
        ('ai_assistant', '0003_remove_user_fk_use_email'),
    ]

    operations = [
        migrations.RunPython(enable_pgvector, disable_pgvector),
    ]
