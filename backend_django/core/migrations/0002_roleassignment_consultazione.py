# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('elections', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='roleassignment',
            name='consultazione',
            field=models.ForeignKey(
                blank=True,
                help_text='Se null, il ruolo è globale (valido per tutte le consultazioni)',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='role_assignments',
                to='elections.consultazioneelettorale',
                verbose_name='consultazione',
            ),
        ),
    ]
