# Generated manually for rdl_registration FK on SectionAssignment

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0005_required_personal_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="sectionassignment",
            name="rdl_registration",
            field=models.ForeignKey(
                blank=True,
                help_text="Origine dal pool RDL approvati",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="section_assignments",
                to="campaign.rdlregistration",
                verbose_name="registrazione RDL",
            ),
        ),
    ]
