"""
Enable pgvector extension for vector similarity search.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('ai_assistant', '0003_remove_user_fk_use_email'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS vector;',
            reverse_sql='DROP EXTENSION IF EXISTS vector;'
        )
    ]
