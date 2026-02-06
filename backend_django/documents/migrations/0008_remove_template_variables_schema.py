from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0007_remove_old_template_type_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='template',
            name='variables_schema',
        ),
    ]
