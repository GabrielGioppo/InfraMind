from django.db import migrations
from django.db.models import Q


def marcar_existentes(apps, schema_editor):
    """Ocorrências que já tiveram algum andamento antes da triagem existir são consideradas triadas;
    as abertas e sem nenhuma definição do administrador continuam como novas."""
    Occurrence = apps.get_model('occurrences', 'Occurrence')
    Occurrence.objects.exclude(status='open').update(triagem='triada')
    Occurrence.objects.filter(status='open').filter(
        Q(importance_color__isnull=False) | Q(prazo_definido__isnull=False)
    ).update(triagem='triada')


class Migration(migrations.Migration):

    dependencies = [
        ('occurrences', '0015_triagem'),
    ]

    operations = [
        migrations.RunPython(marcar_existentes, migrations.RunPython.noop),
    ]
