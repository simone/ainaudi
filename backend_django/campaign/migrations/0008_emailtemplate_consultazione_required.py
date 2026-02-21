"""
Rende EmailTemplate.consultazione obbligatoria (non-nullable).

Step 1: assegna la consultazione più recente a tutti i template senza consultazione
Step 2: altera il campo a non-nullable con on_delete=CASCADE
"""
import django.db.models.deletion
from django.db import migrations, models


def fix_null_consultazione(apps, schema_editor):
    EmailTemplate = apps.get_model('campaign', 'EmailTemplate')
    ConsultazioneElettorale = apps.get_model('elections', 'ConsultazioneElettorale')

    nulls = EmailTemplate.objects.filter(consultazione__isnull=True)
    if not nulls.exists():
        return

    consultazione = ConsultazioneElettorale.objects.order_by('-data_inizio').first()
    if consultazione:
        nulls.update(consultazione=consultazione)
    else:
        # Nessuna consultazione disponibile: elimina i template orfani
        nulls.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0007_fixture_corso_formazione_rdl'),
        ('elections', '0004_add_data_version_and_has_subdelegations'),
    ]

    operations = [
        migrations.RunPython(fix_null_consultazione, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='emailtemplate',
            name='consultazione',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='email_templates',
                to='elections.consultazioneelettorale',
                verbose_name='consultazione',
            ),
        ),
    ]
