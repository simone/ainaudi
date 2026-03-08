"""
Add embedding vector field to KnowledgeSource for similarity search.
"""
from django.db import connection, migrations
import pgvector.django


def create_hnsw_index(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute('''
            CREATE INDEX IF NOT EXISTS knowledgesource_embedding_idx
            ON ai_assistant_knowledgesource
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        ''')


def drop_hnsw_index(apps, schema_editor):
    if connection.vendor == 'postgresql':
        schema_editor.execute('DROP INDEX IF EXISTS knowledgesource_embedding_idx;')


class Migration(migrations.Migration):
    dependencies = [
        ('ai_assistant', '0004_enable_pgvector'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgesource',
            name='embedding',
            field=pgvector.django.VectorField(dimensions=768, null=True, blank=True),
        ),
        migrations.RunPython(create_hnsw_index, drop_hnsw_index),
    ]
