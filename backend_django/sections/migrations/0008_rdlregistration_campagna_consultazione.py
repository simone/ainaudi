# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0007_fix_assignment_fk_to_rdl'),
        ('elections', '0001_initial'),
        ('delegations', '0009_campagnareclutamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='rdlregistration',
            name='campagna',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='registrazioni',
                to='delegations.campagnareclutamento',
                verbose_name='campagna di reclutamento',
            ),
        ),
        migrations.AddField(
            model_name='rdlregistration',
            name='consultazione',
            field=models.ForeignKey(
                blank=True,
                help_text="Consultazione per cui l'RDL si è registrato",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rdl_registrations',
                to='elections.consultazioneelettorale',
                verbose_name='consultazione',
            ),
        ),
        migrations.AlterField(
            model_name='rdlregistration',
            name='source',
            field=models.CharField(
                choices=[
                    ('SELF', 'Auto-registrazione'),
                    ('IMPORT', 'Import CSV'),
                    ('MANUAL', 'Inserimento manuale'),
                    ('CAMPAGNA', 'Campagna di reclutamento'),
                ],
                default='SELF',
                max_length=20,
                verbose_name='origine',
            ),
        ),
    ]
