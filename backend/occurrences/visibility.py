"""
Quem enxerga qual ocorrência.

- Administrador: todas.
- Cidadão: as ocorrências da cidade onde mora (cidade + UF do cadastro) e as que
  ele mesmo registrou, em qualquer cidade.
"""

from django.db.models import Q

from occurrences.models import Occurrence
from users.validators import chave_cidade


def is_admin(user) -> bool:
    return user.user_type == 'admin' or user.is_staff


def visible_occurrences(user, queryset=None):
    qs = Occurrence.objects.all() if queryset is None else queryset
    if is_admin(user):
        return qs
    filtro = Q(user=user)
    cidade = chave_cidade(user.cidade)
    uf = (user.uf or '').strip().upper()
    if cidade and uf:
        filtro |= Q(city_key=cidade, state=uf)
    return qs.filter(filtro)
