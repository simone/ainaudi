# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('delegations', '0008_subdelega_regioni_province'),
        ('elections', '0001_initial'),
        ('territorio', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CampagnaReclutamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome identificativo della campagna', max_length=200, verbose_name='nome')),
                ('slug', models.SlugField(help_text='URL pubblico: /campagna/{slug}', max_length=100, unique=True, verbose_name='slug')),
                ('descrizione', models.TextField(blank=True, help_text='Descrizione mostrata nella pagina di registrazione', verbose_name='descrizione')),
                ('data_apertura', models.DateTimeField(help_text='Quando la campagna diventa accessibile', verbose_name='data apertura')),
                ('data_chiusura', models.DateTimeField(help_text='Quando la campagna termina', verbose_name='data chiusura')),
                ('stato', models.CharField(choices=[('BOZZA', 'Bozza'), ('ATTIVA', 'Attiva'), ('CHIUSA', 'Chiusa')], default='BOZZA', max_length=15, verbose_name='stato')),
                ('richiedi_approvazione', models.BooleanField(default=True, help_text='Se True, le registrazioni devono essere approvate manualmente', verbose_name='richiedi approvazione')),
                ('max_registrazioni', models.IntegerField(blank=True, help_text='Numero massimo di registrazioni (null = illimitato)', null=True, verbose_name='max registrazioni')),
                ('messaggio_conferma', models.TextField(blank=True, help_text='Messaggio mostrato dopo la registrazione', verbose_name='messaggio conferma')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='data creazione')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='data modifica')),
                ('consultazione', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campagne_reclutamento', to='elections.consultazioneelettorale', verbose_name='consultazione')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campagne_create', to=settings.AUTH_USER_MODEL, verbose_name='creato da')),
                ('delegato', models.ForeignKey(blank=True, help_text='Delegato che ha creato la campagna', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='campagne_reclutamento', to='delegations.delegatodilista', verbose_name='delegato')),
                ('sub_delega', models.ForeignKey(blank=True, help_text='Sub-delegato che ha creato la campagna', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='campagne_reclutamento', to='delegations.subdelega', verbose_name='sub-delega')),
                ('territorio_comuni', models.ManyToManyField(blank=True, help_text='Comuni dove è possibile registrarsi', related_name='campagne_reclutamento', to='territorio.comune', verbose_name='comuni')),
                ('territorio_province', models.ManyToManyField(blank=True, help_text='Province dove è possibile registrarsi', related_name='campagne_reclutamento', to='territorio.provincia', verbose_name='province')),
                ('territorio_regioni', models.ManyToManyField(blank=True, help_text='Regioni dove è possibile registrarsi', related_name='campagne_reclutamento', to='territorio.regione', verbose_name='regioni')),
            ],
            options={
                'verbose_name': 'Campagna di Reclutamento',
                'verbose_name_plural': 'Campagne di Reclutamento',
                'ordering': ['-data_apertura'],
            },
        ),
        migrations.AddIndex(
            model_name='campagnareclutamento',
            index=models.Index(fields=['slug'], name='delegations_slug_d3b8d0_idx'),
        ),
        migrations.AddIndex(
            model_name='campagnareclutamento',
            index=models.Index(fields=['stato', 'data_apertura', 'data_chiusura'], name='delegations_stato_d6f547_idx'),
        ),
    ]
