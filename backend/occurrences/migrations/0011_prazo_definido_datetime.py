from datetime import datetime, time

from django.db import migrations, models
from django.utils import timezone


def data_para_fim_do_dia(apps, schema_editor):
    """Prazos antigos (só data) viram a data às 23:59:59, que é como já eram tratados."""
    Occurrence = apps.get_model('occurrences', 'Occurrence')
    for occ in Occurrence.objects.exclude(prazo_definido__isnull=True):
        fim = datetime.combine(occ.prazo_definido, time(23, 59, 59))
        occ.prazo_definido_novo = timezone.make_aware(fim)
        occ.save(update_fields=['prazo_definido_novo'])


def fim_do_dia_para_data(apps, schema_editor):
    Occurrence = apps.get_model('occurrences', 'Occurrence')
    for occ in Occurrence.objects.exclude(prazo_definido_novo__isnull=True):
        occ.prazo_definido = timezone.localtime(occ.prazo_definido_novo).date()
        occ.save(update_fields=['prazo_definido'])


class Migration(migrations.Migration):

    dependencies = [
        ('occurrences', '0010_occurrence_prazo_definido'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='prazo_definido_novo',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(data_para_fim_do_dia, fim_do_dia_para_data),
        migrations.RemoveField(model_name='occurrence', name='prazo_definido'),
        migrations.RenameField(
            model_name='occurrence', old_name='prazo_definido_novo', new_name='prazo_definido',
        ),
        migrations.AlterField(
            model_name='occurrence',
            name='prazo_definido',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Prazo definido pelo administrador',
            ),
        ),
    ]
