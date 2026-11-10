from django.db import migrations

# Setores (Category) e suas subcategorias. Cada setor tem um gestor público e uma equipe técnica.
CATALOGO = [
    ("Saneamento básico", "Água, esgoto e tratamento: abastecimento, vazamentos e redes de esgoto.", [
        "Esgoto entupido ou vazando", "Vazamento de água na rua", "Falta de água",
        "Esgoto a céu aberto", "Mau cheiro de esgoto", "Tampa de caixa de esgoto danificada",
    ]),
    ("Iluminação pública", "Postes, lâmpadas e fiação da iluminação das vias e praças.", [
        "Poste caído", "Lâmpada queimada", "Poste piscando ou com defeito", "Fiação exposta ou furtada",
        "Falta de iluminação (rua escura)", "Iluminação acesa durante o dia",
    ]),
    ("Vias e pavimentação", "Ruas, calçadas e ciclovias: buracos, asfalto e passeios.", [
        "Buraco na via", "Asfalto danificado", "Calçada quebrada", "Meio-fio danificado", "Ciclovia danificada",
    ]),
    ("Trânsito e sinalização", "Semáforos, placas e sinalização horizontal e vertical.", [
        "Semáforo com defeito", "Placa danificada ou ausente", "Faixa de pedestre apagada",
        "Lombada ou redutor necessário",
    ]),
    ("Drenagem e alagamentos", "Escoamento da água da chuva: bueiros, bocas de lobo e galerias.", [
        "Bueiro entupido", "Bueiro sem tampa", "Boca de lobo entupida", "Ponto de alagamento",
        "Galeria ou canal danificado", "Córrego assoreado",
    ]),
    ("Limpeza urbana e resíduos", "Coleta de lixo, entulho e descarte irregular.", [
        "Lixo acumulado", "Entulho em calçada ou via", "Coleta não realizada", "Descarte irregular de resíduos",
        "Descarte de resíduos perigosos", "Terreno baldio com lixo",
    ]),
    ("Áreas verdes e arborização", "Árvores, praças e canteiros: podas, quedas e manutenção.", [
        "Árvore caída", "Galho em fio de energia", "Poda necessária", "Praça mal conservada", "Mato alto",
    ]),
    ("Defesa civil e riscos", "Riscos a pessoas e imóveis: desabamentos, deslizamentos e erosões.", [
        "Área de risco (deslizamento ou enchente)", "Imóvel com risco de desabamento", "Cratera ou erosão",
    ]),
    ("Transporte público", "Pontos, abrigos e linhas de ônibus.", [
        "Ponto de ônibus danificado", "Abrigo quebrado", "Linha sem atendimento",
    ]),
    ("Espaços públicos e equipamentos", "Praças, quadras, brinquedos, bancos e patrimônio público.", [
        "Brinquedo quebrado", "Banco ou lixeira danificada", "Quadra esportiva danificada",
        "Pichação ou vandalismo",
    ]),
    ("Meio ambiente e saúde pública", "Foco de dengue, poluição, queimadas e áreas protegidas.", [
        "Foco de dengue (água parada)", "Animal morto na via", "Poluição sonora", "Queimada",
        "Ocupação irregular de área protegida",
    ]),
    ("Outros", "Problemas que não se encaixam nos demais setores.", [
        "Outro problema urbano",
    ]),
]

# Categorias antigas (planas) -> (setor, subcategoria). As ocorrências delas são movidas.
CATEGORIAS_ANTIGAS = {
    "Buraco na Via": ("Vias e pavimentação", "Buraco na via"),
    "Bueiro Entupido": ("Drenagem e alagamentos", "Bueiro entupido"),
    "Semáforo Quebrado": ("Trânsito e sinalização", "Semáforo com defeito"),
    "Ponto de Ônibus Danificado": ("Transporte público", "Ponto de ônibus danificado"),
    "Queda de Árvore em Via Pública": ("Áreas verdes e arborização", "Árvore caída"),
    "Furto de Fios e Cabos de Energia": ("Iluminação pública", "Fiação exposta ou furtada"),
    "Vazamento de Água em Via Pública": ("Saneamento básico", "Vazamento de água na rua"),
    "Assalto em Via Pública por Falha de Iluminação": ("Iluminação pública", "Falta de iluminação (rua escura)"),
    "Descarte Irregular de Entulho": ("Limpeza urbana e resíduos", "Entulho em calçada ou via"),
    "Descarte Clandestino de Carga Roubada ou Resíduos Perigosos": ("Limpeza urbana e resíduos", "Descarte de resíduos perigosos"),
    "Vandalismo e Depredação do Patrimônio Público": ("Espaços públicos e equipamentos", "Pichação ou vandalismo"),
    "Invasão e Ocupação Irregular de Áreas Protegidas": ("Meio ambiente e saúde pública", "Ocupação irregular de área protegida"),
    "Gestão Ineficiente de Resíduos Sólidos": ("Limpeza urbana e resíduos", "Coleta não realizada"),
    "Vulnerabilidade a Desastres Ambientais Urbanos": ("Defesa civil e riscos", "Área de risco (deslizamento ou enchente)"),
    "Degradação da Infraestrutura Viária e de Transportes": ("Vias e pavimentação", "Calçada quebrada"),
    "Escassez e Desperdício de Recursos Hídricos": ("Saneamento básico", "Falta de água"),
    "Ineficiência Energética Urbana": ("Iluminação pública", "Iluminação acesa durante o dia"),
}


def aplicar_catalogo(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    Subcategory = apps.get_model('categories', 'Subcategory')
    Occurrence = apps.get_model('occurrences', 'Occurrence')

    setores, subs = {}, {}
    for nome, descricao, subcategorias in CATALOGO:
        setor, criado = Category.objects.get_or_create(
            name=nome, defaults={'description': descricao, 'is_active': True})
        if not criado and not setor.is_active:
            setor.is_active = True
            setor.save(update_fields=['is_active'])
        setores[nome] = setor
        for sub_nome in subcategorias:
            subs[(nome, sub_nome)], _ = Subcategory.objects.get_or_create(
                category=setor, name=sub_nome, defaults={'is_active': True})

    for antigo, (setor_nome, sub_nome) in CATEGORIAS_ANTIGAS.items():
        for cat in Category.objects.filter(name=antigo):
            Occurrence.objects.filter(category=cat).update(
                category=setores[setor_nome], subcategory=subs[(setor_nome, sub_nome)])
            if not Occurrence.objects.filter(category=cat).exists():
                cat.delete()
            else:  # não deveria ocorrer; mantém a categoria antiga se algo sobrou
                cat.is_active = False
                cat.save(update_fields=['is_active'])


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0004_subcategoria'),
        ('occurrences', '0014_subcategoria'),
    ]

    operations = [
        migrations.RunPython(aplicar_catalogo, migrations.RunPython.noop),
    ]
