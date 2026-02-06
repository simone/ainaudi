# Generated migration for refactoring DesignazioneRDL from "1 per RDL" to "1 per station" with snapshot fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('delegations', '0011_delete_campagnareclutamento'),
        ('elections', '0001_initial'),
        ('territory', '0001_initial'),
    ]

    operations = [
        # Step 1: Delete old DesignazioneRDL model
        migrations.DeleteModel(
            name='DesignazioneRDL',
        ),

        # Step 2: Recreate DesignazioneRDL with snapshot fields (no FK to RdlRegistration)
        migrations.CreateModel(
            name='DesignazioneRDL',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),

                # Designante (chi fa la designazione)
                ('delegato', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='designazioni_rdl_dirette',
                    to='delegations.delegatodilista',
                    verbose_name='delegato',
                    help_text='Se la designazione è fatta direttamente dal Delegato'
                )),
                ('sub_delega', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='designazioni_rdl',
                    to='delegations.subdelega',
                    verbose_name='sub-delega',
                    help_text='Se la designazione è fatta dal Sub-Delegato'
                )),

                # Sezione elettorale
                ('sezione', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='designazioni_rdl',
                    to='territory.sezioneelettorale',
                    verbose_name='sezione'
                )),

                # RDL EFFETTIVO - Snapshot dei dati
                ('effettivo_cognome', models.CharField(blank=True, max_length=100, verbose_name='effettivo cognome')),
                ('effettivo_nome', models.CharField(blank=True, max_length=100, verbose_name='effettivo nome')),
                ('effettivo_email', models.EmailField(blank=True, max_length=254, verbose_name='effettivo email')),
                ('effettivo_telefono', models.CharField(blank=True, max_length=20, verbose_name='effettivo telefono')),
                ('effettivo_luogo_nascita', models.CharField(blank=True, max_length=100, verbose_name='effettivo luogo nascita')),
                ('effettivo_data_nascita', models.DateField(blank=True, null=True, verbose_name='effettivo data nascita')),
                ('effettivo_domicilio', models.CharField(blank=True, max_length=255, verbose_name='effettivo domicilio')),

                # RDL SUPPLENTE - Snapshot dei dati
                ('supplente_cognome', models.CharField(blank=True, max_length=100, verbose_name='supplente cognome')),
                ('supplente_nome', models.CharField(blank=True, max_length=100, verbose_name='supplente nome')),
                ('supplente_email', models.EmailField(blank=True, max_length=254, verbose_name='supplente email')),
                ('supplente_telefono', models.CharField(blank=True, max_length=20, verbose_name='supplente telefono')),
                ('supplente_luogo_nascita', models.CharField(blank=True, max_length=100, verbose_name='supplente luogo nascita')),
                ('supplente_data_nascita', models.DateField(blank=True, null=True, verbose_name='supplente data nascita')),
                ('supplente_domicilio', models.CharField(blank=True, max_length=255, verbose_name='supplente domicilio')),

                # Stato
                ('stato', models.CharField(
                    max_length=15,
                    choices=[
                        ('BOZZA', 'Bozza (in attesa approvazione Delegato)'),
                        ('CONFERMATA', 'Confermata'),
                        ('REVOCATA', 'Revocata'),
                    ],
                    default='BOZZA',
                    verbose_name='stato',
                    help_text='BOZZA = mappatura in attesa di approvazione del Delegato'
                )),
                ('data_designazione', models.DateField(auto_now_add=True, verbose_name='data designazione')),
                ('is_attiva', models.BooleanField(default=True, verbose_name='attiva')),

                # Approvazione
                ('approvata_da_email', models.EmailField(
                    blank=True,
                    max_length=254,
                    verbose_name='approvata da (email)',
                    help_text='Email del Delegato che ha approvato la bozza'
                )),
                ('data_approvazione', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='data approvazione'
                )),

                # Batch PDF
                ('batch_pdf', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='designazioni',
                    to='delegations.batchgenerazionedocumenti',
                    verbose_name='batch PDF',
                    help_text='Batch di generazione PDF associato'
                )),

                # Revoca
                ('revocata_il', models.DateField(blank=True, null=True, verbose_name='revocata il')),
                ('motivo_revoca', models.TextField(blank=True, verbose_name='motivo revoca')),

                # Audit
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='data creazione')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='data modifica')),
                ('created_by_email', models.EmailField(blank=True, max_length=254, verbose_name='creato da (email)')),
            ],
            options={
                'verbose_name': 'Designazione RDL',
                'verbose_name_plural': 'Designazioni RDL',
                'ordering': ['sezione'],
            },
        ),

        # Step 3: Add constraints
        migrations.AddConstraint(
            model_name='designazionerdl',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_attiva', True), ('stato', 'CONFERMATA')),
                fields=('sezione',),
                name='unique_designazione_confermata_per_sezione'
            ),
        ),
        migrations.AddConstraint(
            model_name='designazionerdl',
            constraint=models.CheckConstraint(
                check=models.Q(('delegato__isnull', False)) | models.Q(('sub_delega__isnull', False)),
                name='designazione_ha_delegante'
            ),
        ),
        migrations.AddConstraint(
            model_name='designazionerdl',
            constraint=models.CheckConstraint(
                check=~models.Q(effettivo_email='', supplente_email=''),
                name='designazione_ha_almeno_un_rdl'
            ),
        ),

        # Step 4: Update BatchGenerazioneDocumenti - Add APPROVATO state
        migrations.AlterField(
            model_name='batchgenerazionedocumenti',
            name='stato',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('BOZZA', 'Bozza'),
                    ('GENERATO', 'Generato'),
                    ('APPROVATO', 'Approvato'),
                    ('INVIATO', 'Inviato'),
                ],
                default='BOZZA',
                verbose_name='stato'
            ),
        ),

        # Note: consultazione FK already exists in the database (added in previous migration attempt)
    ]
