# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delegations', '0006_add_is_active_to_batch'),
        ('elections', '0001_initial'),
        ('territory', '0001_initial'),
    ]

    operations = [
        # 1. Rinomina il modello DelegatoDiLista → Delegato
        migrations.RenameModel(
            old_name='DelegatoDiLista',
            new_name='Delegato',
        ),

        # 2. Rinomina la tabella nel database
        migrations.AlterModelTable(
            name='delegato',
            table='delegations_delegato',
        ),

        # 3. Aggiorna Meta (verbose_name, unique_together)
        migrations.AlterModelOptions(
            name='delegato',
            options={
                'ordering': ['consultazione', 'cognome', 'nome'],
                'verbose_name': 'Delegato',
                'verbose_name_plural': 'Delegati',
            },
        ),

        # 4. Aggiorna unique_together (rimuove data_nascita)
        migrations.AlterUniqueTogether(
            name='delegato',
            unique_together={('consultazione', 'cognome', 'nome')},
        ),

        # 5. Rendi opzionali i campi che non sono (nome, cognome, consultazione)
        migrations.AlterField(
            model_name='delegato',
            name='luogo_nascita',
            field=models.CharField(blank=True, max_length=100, verbose_name='luogo di nascita'),
        ),
        migrations.AlterField(
            model_name='delegato',
            name='data_nascita',
            field=models.DateField(blank=True, null=True, verbose_name='data di nascita'),
        ),
        migrations.AlterField(
            model_name='delegato',
            name='carica',
            field=models.CharField(blank=True, choices=[('DEPUTATO', 'Deputato'), ('SENATORE', 'Senatore'), ('CONSIGLIERE_REGIONALE', 'Consigliere Regionale'), ('CONSIGLIERE_COMUNALE', 'Consigliere Comunale'), ('EURODEPUTATO', 'Europarlamentare'), ('RAPPRESENTANTE_PARTITO', 'Rappresentante del Partito')], max_length=30, verbose_name='carica'),
        ),
        migrations.AlterField(
            model_name='delegato',
            name='data_nomina',
            field=models.DateField(blank=True, null=True, verbose_name='data nomina'),
        ),

        # 6. Rinomina i campi M2M territorio (territorio_regioni → regioni, etc.)
        migrations.RenameField(
            model_name='delegato',
            old_name='territorio_regioni',
            new_name='regioni',
        ),
        migrations.RenameField(
            model_name='delegato',
            old_name='territorio_province',
            new_name='province',
        ),
        migrations.RenameField(
            model_name='delegato',
            old_name='territorio_comuni',
            new_name='comuni',
        ),
        migrations.RenameField(
            model_name='delegato',
            old_name='territorio_municipi',
            new_name='municipi',
        ),

        # 7. Aggiorna il related_name per ForeignKey in ConsultazioneElettorale
        migrations.AlterField(
            model_name='delegato',
            name='consultazione',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='delegati',
                to='elections.consultazioneelettorale',
                verbose_name='consultazione'
            ),
        ),

        # 8. Aggiorna l'upload path per documento_nomina
        migrations.AlterField(
            model_name='delegato',
            name='documento_nomina',
            field=models.FileField(
                blank=True,
                help_text='PDF della nomina dal Partito',
                null=True,
                upload_to='deleghe/nomine/',
                verbose_name='documento nomina'
            ),
        ),
    ]
