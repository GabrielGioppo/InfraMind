"""
Perfis do sistema.

- citizen        Cidadão
- admin          Administrador (vê e faz tudo)
- gestor         Gestor Público: cuida de UM setor em UMA cidade
- equipe_tecnica Equipe Técnica: executa o atendimento do setor/cidade dela (só altera o status)

O setor (`User.setor`) e a cidade/UF do cadastro definem o que o gestor e a equipe enxergam.
"""

CIDADAO = 'citizen'
ADMIN = 'admin'
GESTOR = 'gestor'
EQUIPE = 'equipe_tecnica'

PERFIS_MUNICIPAIS = (GESTOR, EQUIPE)


def is_admin(user) -> bool:
    return user.user_type == ADMIN or user.is_staff


def is_gestor(user) -> bool:
    return user.user_type == GESTOR


def is_equipe(user) -> bool:
    return user.user_type == EQUIPE


def is_municipal(user) -> bool:
    """Gestor público ou equipe técnica (perfis ligados a um setor + cidade)."""
    return user.user_type in PERFIS_MUNICIPAIS


def usa_painel(user) -> bool:
    """Quem entra no painel administrativo (admin.html), com recursos conforme o perfil."""
    return is_admin(user) or is_municipal(user)
