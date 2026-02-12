"""
Add embedding vector field to KnowledgeSource for similarity search.
"""
from django.db import migrations
import pgvector.django


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
        # HNSW index for fast approximate nearest neighbor search
        migrations.RunSQL(
            sql='''
                CREATE INDEX IF NOT EXISTS knowledgesource_embedding_idx
                ON ai_assistant_knowledgesource
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            ''',
            reverse_sql='DROP INDEX IF EXISTS knowledgesource_embedding_idx;'
        ),
    ]
