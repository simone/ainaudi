"""
Migration: Replace TemplateType FK with CharField TextChoices.

Steps:
1. Add temporary CharField 'template_type_code'
2. Populate from FK JOIN (template_type -> TemplateType.code)
3. Remove FK 'template_type'
4. Rename 'template_type_code' -> 'template_type'
5. Drop TemplateType table
"""
from django.db import migrations, models


def populate_template_type_code(apps, schema_editor):
    """Copy TemplateType.code into Template.template_type_code."""
    Template = apps.get_model('documents', 'Template')
    for template in Template.objects.select_related('template_type').all():
        if template.template_type:
            template.template_type_code = template.template_type.code
            template.save(update_fields=['template_type_code'])


def reverse_populate(apps, schema_editor):
    """Reverse: copy template_type string back to FK."""
    Template = apps.get_model('documents', 'Template')
    TemplateType = apps.get_model('documents', 'TemplateType')
    for template in Template.objects.all():
        if template.template_type:
            tt = TemplateType.objects.filter(code=template.template_type).first()
            if tt:
                template.template_type_id = tt.id
                template.save(update_fields=['template_type_id'])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0010_add_template_owner"),
    ]

    operations = [
        # Step 1: Add temporary CharField
        migrations.AddField(
            model_name="template",
            name="template_type_code",
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                verbose_name="tipo template (codice)",
            ),
        ),
        # Step 2: Populate from FK
        migrations.RunPython(populate_template_type_code, reverse_populate),
        # Step 3: Remove FK
        migrations.RemoveField(
            model_name="template",
            name="template_type",
        ),
        # Step 4: Rename temp field to template_type
        migrations.RenameField(
            model_name="template",
            old_name="template_type_code",
            new_name="template_type",
        ),
        # Step 5: Alter field to add choices and remove blank/default
        migrations.AlterField(
            model_name="template",
            name="template_type",
            field=models.CharField(
                choices=[
                    ("DESIGNATION_SINGLE", "Designazione RDL Singola"),
                    ("DESIGNATION_MULTI", "Designazione RDL Riepilogativa"),
                    ("DELEGATION", "Delega Sub-Delegato"),
                ],
                help_text="Tipo di template che definisce schema e modalità unione",
                max_length=50,
                verbose_name="tipo template",
            ),
        ),
        # Step 6: Drop TemplateType table
        migrations.DeleteModel(
            name="TemplateType",
        ),
    ]
