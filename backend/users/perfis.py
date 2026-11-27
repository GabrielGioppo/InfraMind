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
    
    return user.user_type in PERFIS_MUNICIPAIS


def usa_painel(user) -> bool:
    
    return is_admin(user) or is_municipal(user)
