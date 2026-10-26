from django.db import migrations


class Migration(migrations.Migration):
    """Junta a ponta da develop (cidade da ocorrência) com a da main (análise de IA)."""

    dependencies = [
        ('occurrences', '0012_cidade_da_ocorrencia'),
        ('occurrences', '0012_merge_20261026_1926'),
    ]

    operations = []
