# Generated migration to add regioni and province to SubDelega

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delegations', '0007_add_tipo_delega_and_stato'),
        ('territorio', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subdelega',
            name='regioni',
            field=models.ManyToManyField(
                blank=True,
                help_text='Regioni di competenza',
                related_name='sub_deleghe',
                to='territorio.regione',
                verbose_name='regioni'
            ),
        ),
        migrations.AddField(
            model_name='subdelega',
            name='province',
            field=models.ManyToManyField(
                blank=True,
                help_text='Province di competenza',
                related_name='sub_deleghe',
                to='territorio.provincia',
                verbose_name='province'
            ),
        ),
    ]
