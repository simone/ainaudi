# Generated migration to replace popolazione/cap with sopra_15000_abitanti

from django.db import migrations, models


def convert_popolazione_to_boolean(apps, schema_editor):
    """Convert popolazione > 15000 to sopra_15000_abitanti = True."""
    Comune = apps.get_model('territory', 'Comune')
    # Update comuni with popolazione > 15000
    Comune.objects.filter(popolazione__gt=15000).update(sopra_15000_abitanti=True)


def reverse_conversion(apps, schema_editor):
    """Reverse migration - cannot restore exact popolazione values."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('territory', '0002_add_territorial_partitions'),
    ]

    operations = [
        # First add the new field with default False
        migrations.AddField(
            model_name='comune',
            name='sopra_15000_abitanti',
            field=models.BooleanField(
                default=False,
                help_text='Indica se il comune ha più di 15.000 abitanti (per sistema elettorale)',
                verbose_name='sopra 15.000 abitanti'
            ),
        ),
        # Convert existing data
        migrations.RunPython(convert_popolazione_to_boolean, reverse_conversion),
        # Remove old fields
        migrations.RemoveField(
            model_name='comune',
            name='popolazione',
        ),
        migrations.RemoveField(
            model_name='comune',
            name='cap',
        ),
    ]
