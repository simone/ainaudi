# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_roleassignment_consultazione'),
    ]

    operations = [
        migrations.DeleteModel(
            name='IdentityProviderLink',
        ),
    ]
