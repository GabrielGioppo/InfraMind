from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrences', '0009_alter_occurrence_latitude_alter_occurrence_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='prazo_definido',
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name='Prazo definido pelo administrador',
            ),
        ),
    ]
