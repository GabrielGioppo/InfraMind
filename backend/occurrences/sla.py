"""
Regra única de prazo (SLA) das ocorrências — UC-14.

Usada tanto pelo serializer (indicador de prazo no painel admin) quanto
pela rotina de notificações (notifications/services.py), para que o que
o painel mostra e o que é notificado nunca divirjam.

O prazo vem de Occurrence.prazo_definido (data escolhida pelo admin no calendário)
e, na falta dela, de Occurrence.estimated_time (horas). Ver `prazo_final`.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone

STATUS_ENCERRADOS = ('resolved', 'closed')

# A1: aviso preventivo quando 80% do prazo já foi consumido.
LIMIAR_AVISO_PREVENTIVO = 0.8

SLA_OK = 'ok'
SLA_PROXIMO = 'proximo'
SLA_ESTOURADO = 'estourado'


def prazo_final(occ):
    """
    Data limite de atendimento, ou None se a ocorrência não tem prazo.

    Prioridade: data escolhida pelo admin (`prazo_definido`, vale até o fim do dia);
    senão, criação + tempo estimado em horas (`estimated_time`).
    """
    if occ.prazo_definido:
        fim_do_dia = datetime.combine(occ.prazo_definido, time(23, 59, 59))
        return timezone.make_aware(fim_do_dia)
    if not occ.estimated_time or occ.estimated_time <= 0:
        return None
    return occ.created_at + timedelta(hours=occ.estimated_time)


def sla_status(occ, agora=None):
    """
    Retorna 'ok', 'proximo' (>= 80% do prazo) ou 'estourado'.
    Retorna None para ocorrência sem prazo ou já encerrada.
    """
    if occ.status in STATUS_ENCERRADOS:
        return None
    limite = prazo_final(occ)
    if limite is None:
        return None

    agora = agora or timezone.now()
    if agora >= limite:
        return SLA_ESTOURADO

    total_h = (limite - occ.created_at).total_seconds() / 3600
    decorrido_h = (agora - occ.created_at).total_seconds() / 3600
    if decorrido_h >= total_h * LIMIAR_AVISO_PREVENTIVO:
        return SLA_PROXIMO
    return SLA_OK
