# Generated manually for cache invalidation timestamp

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0003_add_partition_bindings_remove_old_circumscriptions'),
    ]

    operations = [
        # Add data_version to ConsultazioneElettorale for cache invalidation
        migrations.AddField(
            model_name='consultazioneelettorale',
            name='data_version',
            field=models.DateTimeField(auto_now=True, help_text='Timestamp per invalidazione cache preload seggi', verbose_name='versione dati'),
        ),
    ]
