"""
Fix index names to comply with Django's 30-char limit.

Migration 0004 created indexes with names > 30 chars. This migration:
1. Removes old indexes from Django state + DB (IF EXISTS for safety)
2. Adds them back with shorter names
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('territory', '0004_add_sezione_performance_indices'),
    ]

    operations = [
        # Remove old indexes from Django migration state
        migrations.RemoveIndex(
            model_name='sezioneelettorale',
            name='territory_sez_active_comune_idx',
        ),
        migrations.RemoveIndex(
            model_name='sezioneelettorale',
            name='territory_sez_active_mun_idx',
        ),
        # Add with new shorter names
        migrations.AddIndex(
            model_name='sezioneelettorale',
            index=models.Index(
                fields=['is_attiva', 'comune'],
                name='terr_sez_attiva_comune_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='sezioneelettorale',
            index=models.Index(
                fields=['is_attiva', 'municipio'],
                name='terr_sez_attiva_mun_idx'
            ),
        ),
    ]
