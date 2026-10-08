"""
UC-14 — Processar Prazos e Disparar Notificações — notifications/services.py

Verifica ocorrências cujo prazo estimado (Occurrence.estimated_time, em
horas) já estourou sem que tenham sido resolvidas/fechadas, e dispara,
via NotificacaoFactory (Factory Method), um aviso para o cidadão que
abriu o chamado e para os administradores — evitando notificar duas
vezes a mesma ocorrência.

Ponto de entrada pensado pra rodar de forma agendada:
`python manage.py processar_prazos` (ver management/commands/), que por
sua vez pode ser chamado por um cron do SO ou, futuramente, Celery beat.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from notifications.factory import EmailNotifFactory, PushNotifFactory
from notifications.models import Notificacao
from occurrences.models import Occurrence

User = get_user_model()

TIPO_PRAZO_ESTOURADO = 'prazo_estourado'

FACTORIES = {
    'email': EmailNotifFactory(),
    'push': PushNotifFactory(),
}

OCCURRENCE_STATUS_ENCERRADOS = ['resolved', 'closed']


def _ja_notificado(occurrence) -> bool:
    """Evita duplicar o aviso de prazo estourado pra mesma ocorrência."""
    return Notificacao.objects.filter(
        occurrence=occurrence, tipo=TIPO_PRAZO_ESTOURADO
    ).exists()


def _occurrences_com_prazo_estourado():
    """
    Ocorrências em aberto/andamento cujo prazo estimado (created_at +
    estimated_time horas) já passou. O filtro de status é feito no banco;
    o cálculo do prazo é feito em Python porque estimated_time é um
    intervalo relativo (horas), não uma data absoluta armazenada.
    """
    agora = timezone.now()
    candidatas = Occurrence.objects.exclude(
        status__in=OCCURRENCE_STATUS_ENCERRADOS
    ).filter(estimated_time__isnull=False)

    return [
        occ for occ in candidatas
        if agora >= occ.created_at + timedelta(hours=occ.estimated_time)
    ]


def _destinatarios_admin():
    return User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).distinct()


def processar_prazos_e_notificar(canal: str = 'email') -> dict:
    """
    Ponto de entrada do UC-14.

    Retorna um resumo {'notificadas': int, 'ignoradas': int} com quantas
    Notificacao foram criadas e quantas ocorrências já haviam sido
    notificadas anteriormente (e por isso foram ignoradas).
    """
    factory = FACTORIES.get(canal, FACTORIES['email'])
    admins = list(_destinatarios_admin())

    notificadas_ids, ignoradas_ids = [], []

    for occ in _occurrences_com_prazo_estourado():
        if _ja_notificado(occ):
            ignoradas_ids.append(occ.id)
            continue

        titulo = f'Prazo estourado — Ocorrência #{occ.id}'
        mensagem = (
            f'A ocorrência "{occ.title}" ultrapassou o prazo estimado de '
            f'{occ.estimated_time}h sem ser resolvida. '
            f'Status atual: {occ.get_status_display()}.'
        )

        destinatarios = admins + ([occ.user] if occ.user else [])
        for destinatario in destinatarios:
            notificacao = factory.notificar(
                destinatario, titulo, mensagem,
                occurrence=occ, tipo=TIPO_PRAZO_ESTOURADO,
            )
            notificadas_ids.append(notificacao.id)

    return {
        'notificadas': len(notificadas_ids),
        'ignoradas': len(ignoradas_ids),
        'ocorrencias_ignoradas': ignoradas_ids,
    }
