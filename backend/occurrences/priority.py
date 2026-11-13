"""
Padrão Strategy — cálculo da prioridade da ocorrência.

Cada regra é uma estratégia com a mesma interface (`calcular(occ) -> int`). Quem precisa da
prioridade chama `calcular_prioridade(occ)` e não sabe qual regra está valendo; trocar a regra é
mudar `PRIORITY_STRATEGY` (variável de ambiente / settings), sem tocar nas views.

    padrao       validações + dias em aberto + importância (comportamento original)
    por_prazo    padrão + peso extra para prazo estourado ou perto de estourar
    urgencia_ia  padrão + nota de urgência calculada pela IA
"""
from abc import ABC, abstractmethod
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from occurrences.sla import STATUS_ENCERRADOS, prazo_final

PESO_COR = {'red': 10, 'yellow': 5, 'green': 0}


class PrioridadeStrategy(ABC):
    nome = ''

    @abstractmethod
    def calcular(self, occ) -> int:
        """Pontuação da ocorrência: quanto maior, mais urgente de atender."""


class PrioridadePadrao(PrioridadeStrategy):
    nome = 'padrao'

    def calcular(self, occ) -> int:
        dias_abertos = (timezone.now() - occ.created_at).days
        return (occ.validation_count * 2
                + min(dias_abertos, 10)
                + PESO_COR.get(occ.importance_color or 'green', 0))


class PrioridadePorPrazo(PrioridadePadrao):
    nome = 'por_prazo'

    def calcular(self, occ) -> int:
        pontos = super().calcular(occ)
        limite = prazo_final(occ)
        if not limite or occ.status in STATUS_ENCERRADOS:
            return pontos
        falta = limite - timezone.now()
        if falta <= timedelta(0):
            return pontos + 20
        if falta <= timedelta(hours=24):
            return pontos + 10
        if falta <= timedelta(hours=72):
            return pontos + 5
        return pontos


class PrioridadePorUrgenciaIA(PrioridadePadrao):
    nome = 'urgencia_ia'

    def calcular(self, occ) -> int:
        return super().calcular(occ) + min(max(occ.urgency_score or 0, 0), 100) // 10


ESTRATEGIAS = {e.nome: e for e in (PrioridadePadrao(), PrioridadePorPrazo(), PrioridadePorUrgenciaIA())}


def estrategia_atual() -> PrioridadeStrategy:
    """Estratégia escolhida em settings.PRIORITY_STRATEGY; nome desconhecido cai no padrão."""
    return ESTRATEGIAS.get(getattr(settings, 'PRIORITY_STRATEGY', 'padrao'), ESTRATEGIAS['padrao'])


def calcular_prioridade(occ) -> int:
    return estrategia_atual().calcular(occ)
