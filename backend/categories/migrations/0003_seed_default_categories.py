from django.db import migrations

DEFAULT_CATEGORIES = [
    ("Buraco na Via", "Buracos, crateras ou irregularidades no asfalto que oferecem risco ao tráfego."),
    ("Bueiro Entupido", "Bueiros obstruídos que causam alagamentos ou acúmulo de água na via."),
    ("Semáforo Quebrado", "Semáforos com defeito, apagados ou em funcionamento irregular."),
    ("Ponto de Ônibus Danificado", "Abrigos ou estruturas de pontos de ônibus quebrados ou depredados."),
    ("Queda de Árvore em Via Pública", "Árvores caídas ou galhos que obstruem calçadas, ruas ou fiações."),
    ("Furto de Fios e Cabos de Energia", "Furto de cabos elétricos ou de telecomunicações causando risco ou interrupção de serviço."),
    ("Vazamento de Água em Via Pública", "Vazamentos visíveis em tubulações ou hidrantes nas vias públicas."),
    ("Assalto em Via Pública por Falha de Iluminação", "Locais sem iluminação pública adequada que favorecem insegurança."),
    ("Descarte Irregular de Entulho", "Descarte de entulho de construção em locais não autorizados."),
    ("Descarte Clandestino de Carga Roubada ou Resíduos Perigosos", "Abandono de resíduos perigosos, cargas roubadas ou materiais tóxicos em vias públicas."),
    ("Vandalismo e Depredação do Patrimônio Público", "Danos a bens públicos como bancos, monumentos, sinalizações e equipamentos urbanos."),
    ("Invasão e Ocupação Irregular de Áreas Protegidas", "Ocupação não autorizada de áreas de preservação ambiental ou espaços públicos protegidos."),
    ("Gestão Ineficiente de Resíduos Sólidos", "Coleta irregular de lixo, pontos de descarte inadequados ou ausência de coleta seletiva."),
    ("Vulnerabilidade a Desastres Ambientais Urbanos", "Áreas com risco de deslizamento, enchente ou outros desastres naturais em contexto urbano."),
    ("Degradação da Infraestrutura Viária e de Transportes", "Problemas gerais em calçadas, sinalização horizontal/vertical, ciclovias ou estruturas viárias."),
    ("Escassez e Desperdício de Recursos Hídricos", "Falta de abastecimento de água ou desperdício visível em instalações públicas."),
    ("Ineficiência Energética Urbana", "Iluminação pública acesa durante o dia, postes com defeito ou desperdício de energia elétrica."),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    for name, description in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            defaults={'description': description, 'is_active': True},
        )


def unseed_categories(apps, schema_editor):
    """Reversão: remove apenas as categorias padrão (pelo nome)."""
    Category = apps.get_model('categories', 'Category')
    names = [name for name, _ in DEFAULT_CATEGORIES]
    Category.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0002_remove_icon_color'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
