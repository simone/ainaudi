# Generated manually - ProcessoDesignazione model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("delegations", "0014_remove_batchgenerazionedocumenti_sub_delega_and_more"),
        ("elections", "0003_add_partition_bindings_remove_old_circumscriptions"),
        ("documents", "0006_migrate_template_types_data"),
    ]

    operations = [
        # Rinomina BatchGenerazioneDocumenti in ProcessoDesignazione
        migrations.RenameModel(
            old_name="BatchGenerazioneDocumenti",
            new_name="ProcessoDesignazione",
        ),

        # Rinomina tabella
        migrations.AlterModelTable(
            name="processodesignazione",
            table="delegations_processodesignazione",
        ),

        # Aggiorna verbose names
        migrations.AlterModelOptions(
            name="processodesignazione",
            options={
                'verbose_name': 'Processo Designazione RDL',
                'verbose_name_plural': 'Processi Designazione RDL',
                'ordering': ['-created_at']
            },
        ),

        # Aggiungi campi template
        migrations.AddField(
            model_name="processodesignazione",
            name="template_individuale",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processi_individuali",
                to="documents.template",
                verbose_name="template individuale",
                help_text="Template per documento individuale (un PDF per sezione)"
            ),
        ),
        migrations.AddField(
            model_name="processodesignazione",
            name="template_cumulativo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processi_cumulativi",
                to="documents.template",
                verbose_name="template cumulativo",
                help_text="Template per documento riepilogativo (PDF multi-pagina)"
            ),
        ),

        # Aggiungi campo delegato (chi fa il processo)
        migrations.AddField(
            model_name="processodesignazione",
            name="delegato",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="processi_designazione",
                to="delegations.delegato",
                verbose_name="delegato",
                help_text="Delegato che avvia il processo (o per cui si generano i documenti)",
                null=True,
                blank=True
            ),
        ),

        # Aggiungi dati_delegato compilati (snapshot per generazione PDF)
        migrations.AddField(
            model_name="processodesignazione",
            name="dati_delegato",
            field=models.JSONField(
                default=dict,
                blank=True,
                verbose_name="dati delegato compilati",
                help_text="Snapshot dati delegato/subdelegato usati per generare PDF"
            ),
        ),

        # Rinomina campo tipo → rimuoviamo perché non serve più
        migrations.RemoveField(
            model_name="processodesignazione",
            name="tipo",
        ),

        # Aggiorna stato (aggiungi SELEZIONE_TEMPLATE, IN_GENERAZIONE, ANNULLATO)
        migrations.AlterField(
            model_name="processodesignazione",
            name="stato",
            field=models.CharField(
                verbose_name="stato",
                max_length=30,
                choices=[
                    ('SELEZIONE_TEMPLATE', 'Selezione Template'),
                    ('BOZZA', 'Bozza (designazioni create)'),
                    ('IN_GENERAZIONE', 'Generazione PDF in corso'),
                    ('GENERATO', 'PDF Generati'),
                    ('APPROVATO', 'Confermato'),
                    ('ANNULLATO', 'Annullato'),
                    ('INVIATO', 'Inviato a Prefettura'),
                ],
                default='SELEZIONE_TEMPLATE'
            ),
        ),

        # Rinomina documento → documento_individuale
        migrations.RenameField(
            model_name="processodesignazione",
            old_name="documento",
            new_name="documento_individuale",
        ),

        # Aggiungi documento_cumulativo
        migrations.AddField(
            model_name="processodesignazione",
            name="documento_cumulativo",
            field=models.FileField(
                upload_to="deleghe/processi/",
                verbose_name="documento cumulativo",
                null=True,
                blank=True
            ),
        ),

        # Aggiungi data_generazione_cumulativo
        migrations.AddField(
            model_name="processodesignazione",
            name="data_generazione_cumulativo",
            field=models.DateTimeField(
                verbose_name="data generazione cumulativo",
                null=True,
                blank=True
            ),
        ),

        # Rinomina data_generazione → data_generazione_individuale
        migrations.RenameField(
            model_name="processodesignazione",
            old_name="data_generazione",
            new_name="data_generazione_individuale",
        ),

        # Rimuovi solo_sezioni (non serve più, usiamo FK su DesignazioneRDL)
        migrations.RemoveField(
            model_name="processodesignazione",
            name="solo_sezioni",
        ),

        # Aggiungi campo approvata_at, approvata_da_email
        migrations.AddField(
            model_name="processodesignazione",
            name="approvata_at",
            field=models.DateTimeField(
                verbose_name="data approvazione",
                null=True,
                blank=True
            ),
        ),
        migrations.AddField(
            model_name="processodesignazione",
            name="approvata_da_email",
            field=models.EmailField(
                verbose_name="approvata da (email)",
                blank=True
            ),
        ),

        # Update DesignazioneRDL FK
        migrations.RenameField(
            model_name="designazionerdl",
            old_name="batch_pdf",
            new_name="processo",
        ),
        migrations.AlterField(
            model_name="designazionerdl",
            name="processo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="designazioni",
                to="delegations.processodesignazione",
                verbose_name="processo designazione",
                help_text="Processo di designazione a cui appartiene questa designazione"
            ),
        ),
    ]
