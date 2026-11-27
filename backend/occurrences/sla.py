from datetime import timedelta

from django.utils import timezone

STATUS_ENCERRADOS = ('resolved', 'closed')

# A1: aviso preventivo quando 80% do prazo já foi consumido.
LIMIAR_AVISO_PREVENTIVO = 0.8

SLA_OK = 'ok'
SLA_PROXIMO = 'proximo'
SLA_ESTOURADO = 'estourado'


def prazo_final(occ):
  
    if occ.prazo_definido:
        return occ.prazo_definido
    if not occ.estimated_time or occ.estimated_time <= 0:
        return None
    return occ.created_at + timedelta(hours=occ.estimated_time)


def sla_status(occ, agora=None):
   
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
