"""
Quem enxerga qual ocorrência.

- Administrador: todas.
- Gestor público e equipe técnica: as ocorrências do SETOR deles na CIDADE deles
  (cidade + UF do cadastro) e as que eles mesmos registraram. Sem setor ou sem
  cidade definidos, só as próprias.
- Cidadão: as ocorrências da cidade onde mora (cidade + UF do cadastro) e as que
  ele mesmo registrou, em qualquer cidade.
"""

from django.db.models import Q

from occurrences.models import Occurrence
from users.perfis import is_admin, is_municipal  # noqa: F401  (is_admin é reexportado)
from users.validators import chave_cidade


def visible_occurrences(user, queryset=None):
    qs = Occurrence.objects.all() if queryset is None else queryset
    if is_admin(user):
        return qs
    filtro = Q(user=user)
    cidade = chave_cidade(user.cidade)
    uf = (user.uf or '').strip().upper()
    if is_municipal(user):
        if user.setor_id and cidade and uf:
            filtro |= Q(category_id=user.setor_id, city_key=cidade, state=uf)
    elif cidade and uf:
        filtro |= Q(city_key=cidade, state=uf)
    return qs.filter(filtro)
