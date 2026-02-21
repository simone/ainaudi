"""
Fixture: tutti i template email (caricati da fixtures/email_templates.json).

Include:
- 4x Corso di formazione RdL (uno per gruppo municipi)
- 1x Invito Piattaforma AInaudi
"""
import json
import os
from django.db import migrations


FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'fixtures', 'email_templates.json'
)


def create_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('campaign', 'EmailTemplate')
    ConsultazioneElettorale = apps.get_model('elections', 'ConsultazioneElettorale')

    consultazione = ConsultazioneElettorale.objects.order_by('-data_inizio').first()
    if not consultazione:
        return

    if not os.path.exists(FIXTURE_PATH):
        return

    with open(FIXTURE_PATH, 'r', encoding='utf-8') as f:
        templates = json.load(f)

    for tpl in templates:
        EmailTemplate.objects.get_or_create(
            nome=tpl['nome'],
            defaults={
                'oggetto': tpl['oggetto'],
                'corpo': tpl['corpo'],
                'consultazione': consultazione,
                'created_by_email': tpl.get('created_by_email', ''),
            },
        )


def remove_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('campaign', 'EmailTemplate')
    with open(FIXTURE_PATH, 'r', encoding='utf-8') as f:
        templates = json.load(f)
    nomi = [t['nome'] for t in templates]
    EmailTemplate.objects.filter(nome__in=nomi).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('campaign', '0006_add_emailtemplate_massemaillog'),
        ('elections', '0004_add_data_version_and_has_subdelegations'),
    ]

    operations = [
        migrations.RunPython(create_templates, remove_templates),
    ]
