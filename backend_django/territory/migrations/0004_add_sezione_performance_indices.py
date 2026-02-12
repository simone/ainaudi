"""
Add performance indices for SezioneElettorale queries.

This migration adds compound indices to optimize the common query pattern:
- Filter by is_attiva + comune_id (for section stats views)
- Filter by is_attiva + municipio_id (for section stats views)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('territory', '0003_replace_popolazione_with_sopra_15000'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='sezioneelettorale',
            index=models.Index(
                fields=['is_attiva', 'comune'],
                name='territory_sez_active_comune_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='sezioneelettorale',
            index=models.Index(
                fields=['is_attiva', 'municipio'],
                name='territory_sez_active_mun_idx'
            ),
        ),
    ]
