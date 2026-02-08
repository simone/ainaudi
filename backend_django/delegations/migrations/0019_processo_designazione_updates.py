# Generated manually 2025-02-08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('territory', '0001_initial'),
        ('delegations', '0018_processodesignazione_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='processodesignazione',
            name='comune',
            field=models.ForeignKey(
                blank=True,
                help_text='Comune per cui si generano le designazioni',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='processi_designazione',
                to='territory.comune',
                verbose_name='comune'
            ),
        ),
        migrations.AlterField(
            model_name='designazionerdl',
            name='processo',
            field=models.ForeignKey(
                blank=True,
                help_text='Processo di designazione a cui appartiene questa designazione',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='designazioni',
                to='delegations.processodesignazione',
                verbose_name='processo designazione'
            ),
        ),
    ]
