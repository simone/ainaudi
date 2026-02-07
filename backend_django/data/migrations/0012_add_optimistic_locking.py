# Generated manually for optimistic locking implementation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0011_rename_sections_se_rdl_reg_f85e02_idx_data_sectio_rdl_reg_826205_idx_and_more'),
    ]

    operations = [
        # Add version, updated_at, updated_by_email to DatiSezione
        migrations.AddField(
            model_name='datisezione',
            name='version',
            field=models.IntegerField(default=0, help_text='Versione per optimistic locking', verbose_name='versione'),
        ),
        migrations.AddField(
            model_name='datisezione',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='ultimo aggiornamento'),
        ),
        migrations.AddField(
            model_name='datisezione',
            name='updated_by_email',
            field=models.EmailField(blank=True, help_text='Email utente ultimo aggiornamento', max_length=254, verbose_name='aggiornato da (email)'),
        ),

        # Add version, updated_at, updated_by_email to DatiScheda
        migrations.AddField(
            model_name='datischeda',
            name='version',
            field=models.IntegerField(default=0, help_text='Versione per optimistic locking', verbose_name='versione'),
        ),
        migrations.AddField(
            model_name='datischeda',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='ultimo aggiornamento'),
        ),
        migrations.AddField(
            model_name='datischeda',
            name='updated_by_email',
            field=models.EmailField(blank=True, help_text='Email utente ultimo aggiornamento', max_length=254, verbose_name='aggiornato da (email)'),
        ),

        # Add indexes for optimistic locking queries
        migrations.AddIndex(
            model_name='datisezione',
            index=models.Index(fields=['sezione', 'consultazione', 'version'], name='data_datise_sezione_version_idx'),
        ),
        migrations.AddIndex(
            model_name='datischeda',
            index=models.Index(fields=['dati_sezione', 'scheda', 'version'], name='data_datisc_datisez_version_idx'),
        ),
    ]
