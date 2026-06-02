# Migration para tornar o campo rating opcional
# Admins podem postar atualizações sem nota

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feedbacks', '0002_feedback_real_resolution_time_feedback_resolved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='rating',
            field=models.IntegerField(
                choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
                null=True,
                blank=True,
                help_text='Nota de 1 a 5. Obrigatória para cidadãos, não disponível para admins.'
            ),
        ),
    ]
