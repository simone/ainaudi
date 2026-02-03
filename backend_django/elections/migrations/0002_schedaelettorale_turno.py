# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elections", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedaelettorale",
            name="turno",
            field=models.IntegerField(
                default=1,
                help_text="1 = primo turno, 2 = ballottaggio",
                verbose_name="turno",
            ),
        ),
        migrations.AddField(
            model_name="schedaelettorale",
            name="data_inizio_turno",
            field=models.DateField(
                null=True,
                blank=True,
                help_text="Per turno=2: data del ballottaggio. Se null, usa data_inizio consultazione",
                verbose_name="data inizio turno",
            ),
        ),
    ]
