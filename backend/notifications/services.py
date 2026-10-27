from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from notifications.factory import EmailNotifFactory, PushNotifFactory
from notifications.models import Notificacao
from occurrences.models import Occurrence
from occurrences.sla import LIMIAR_AVISO_PREVENTIVO, STATUS_ENCERRADOS, prazo_final
from history.models import OccurrenceHistory

User = get_user_model()

TIPO_PRAZO_ESTOURADO = 'prazo_estourado'
TIPO_AVISO_PRAZO     = 'aviso_prazo'
TIPO_STATUS_CHANGE   = 'status_change'

# Título dos avisos de denúncia; o painel admin usa o prefixo para abrir a aba Denúncias.
TITULO_NOVA_DENUNCIA = 'Nova denúncia'

FACTORIES = {
    'email': EmailNotifFactory(),
    'push':  PushNotifFactory(),
}

# Regra de prazo compartilhada com o painel admin (occurrences/sla.py).
OCCURRENCE_STATUS_ENCERRADOS = list(STATUS_ENCERRADOS)


def _ja_notificado(occurrence, tipo: str) -> bool:
    """
    Evita duplicar o aviso pra mesma ocorrência — mas só conta notificações
    que realmente saíram (status='enviada'). Uma notificação que falhou
    (E1) NÃO conta como "já notificado", pra ser reenviada na próxima
    execução da rotina, como pede o fluxo de exceção.
    """
    return Notificacao.objects.filter(
        occurrence=occurrence, tipo=tipo, status='enviada',
    ).exists()


def _occurrences_ativas_com_prazo():
    return Occurrence.objects.exclude(
        status__in=OCCURRENCE_STATUS_ENCERRADOS
    ).filter(Q(prazo_definido__isnull=False) | Q(estimated_time__isnull=False))


def _descrever_prazo(occ) -> str:
    """Texto do prazo nas mensagens: data escolhida pelo admin ou horas estimadas."""
    if occ.prazo_definido:
        return f'até {timezone.localtime(occ.prazo_definido).strftime("%d/%m/%Y %H:%M")}'
    return f'{occ.estimated_time}h estimadas'


def _destinatarios_admin():
    """
    Equipe Técnica e Gestor Público ainda não existem como papéis
    próprios no model de usuário (isso é o UC-08/UC-09, pendente) — por
    ora, todo usuário admin/staff recebe esses avisos. Quando esses
    papéis existirem, trocar esse filtro pra mirar neles especificamente.
    """
    return list(User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).distinct())


def _processar_prazo_estourado(factory, admins) -> list:
    """Fluxo principal (passos 2-6) — prazo já ultrapassado."""
    agora = timezone.now()
    notificadas_ids = []

    for occ in _occurrences_ativas_com_prazo():
        limite = prazo_final(occ)
        if limite is None or agora < limite:
            continue
        if _ja_notificado(occ, TIPO_PRAZO_ESTOURADO):
            continue

        titulo = f'Prazo estourado — Ocorrência #{occ.id}'
        mensagem = (
            f'A ocorrência "{occ.title}" ultrapassou o prazo '
            f'({_descrever_prazo(occ)}) sem ser resolvida. '
            f'Status atual: {occ.get_status_display()}.'
        )
        # Dedup por id: um admin que é dono da ocorrência não recebe duas vezes.
        destinatarios = list({u.id: u for u in admins + ([occ.user] if occ.user else [])}.values())
        for destinatario in destinatarios:
            notificacao = factory.notificar(
                destinatario, titulo, mensagem,
                occurrence=occ, tipo=TIPO_PRAZO_ESTOURADO,
            )
            notificadas_ids.append(notificacao.id)

    return notificadas_ids


def _processar_aviso_preventivo(factory, admins) -> list:
    """
    Fluxo alternativo A1 (ocorre no passo 3) — ocorrência atingiu 80% do
    prazo sem ser concluída: aviso preventivo pra Equipe Técnica e Gestor
    Público (hoje: admins), prioridade amarela.
    """
    agora = timezone.now()
    notificadas_ids = []

    for occ in _occurrences_ativas_com_prazo():
        limite = prazo_final(occ)
        if limite is None:
            continue
        prazo_total_h = (limite - occ.created_at).total_seconds() / 3600
        decorrido_h = (agora - occ.created_at).total_seconds() / 3600
        if prazo_total_h <= 0 or decorrido_h < prazo_total_h * LIMIAR_AVISO_PREVENTIVO:
            continue
        if decorrido_h >= prazo_total_h:
            continue  # já estourou — vira prazo_estourado, não aviso preventivo
        if _ja_notificado(occ, TIPO_AVISO_PRAZO):
            continue

        titulo = f'Atenção: prazo próximo do limite — Ocorrência #{occ.id}'
        mensagem = (
            f'A ocorrência "{occ.title}" já consumiu mais de 80% do prazo '
            f'({_descrever_prazo(occ)}) sem ser concluída.'
        )
        for destinatario in admins:
            notificacao = factory.notificar(
                destinatario, titulo, mensagem,
                occurrence=occ, tipo=TIPO_AVISO_PRAZO,
            )
            notificadas_ids.append(notificacao.id)

    return notificadas_ids


def _processar_mudancas_status(factory) -> list:
    """
    Passo 2/5 do fluxo principal — notifica o cidadão quando o status da
    ocorrência dele muda, usando o histórico (OccurrenceHistory) como
    fonte, marcando cada entrada como notified=True pra não duplicar.
    """
    notificadas_ids = []
    pendentes = OccurrenceHistory.objects.filter(
        notified=False, change_type='status',
    ).select_related('occurrence', 'occurrence__user')

    for hist in pendentes:
        occ = hist.occurrence
        if occ.user:
            titulo = f'Atualização na sua ocorrência #{occ.id}'
            mensagem = (
                f'A ocorrência "{occ.title}" mudou de status: '
                f'{hist.previous_status or "—"} → {hist.new_status or "—"}.'
            )
            notificacao = factory.notificar(
                occ.user, titulo, mensagem,
                occurrence=occ, tipo=TIPO_STATUS_CHANGE,
            )
            notificadas_ids.append(notificacao.id)

        hist.notified = True
        hist.save(update_fields=['notified'])

    return notificadas_ids


def processar_prazos_e_notificar(canal: str = 'email') -> dict:
    """
    Ponto de entrada do UC-14. Executa, nessa ordem, os três processamentos
    do caso de uso e retorna um resumo com quantas notificações foram
    efetivamente criadas/enviadas em cada frente.
    """
    factory = FACTORIES.get(canal, FACTORIES['email'])
    admins = _destinatarios_admin()

    prazo_estourado = _processar_prazo_estourado(factory, admins)
    aviso_preventivo = _processar_aviso_preventivo(factory, admins)
    status_change = _processar_mudancas_status(factory)

    return {
        'prazo_estourado':  len(prazo_estourado),
        'aviso_preventivo': len(aviso_preventivo),
        'status_change':    len(status_change),
        'total':            len(prazo_estourado) + len(aviso_preventivo) + len(status_change),
    }


def notificar_nova_denuncia(denuncia) -> list:
    """
    Avisa no sino de todos os administradores que chegou uma denúncia
    (UC-13 → UC-14). Canal push: aparece só no painel, sem depender de e-mail.
    Nunca levanta exceção — a denúncia já foi salva e não pode falhar por causa do aviso.
    """
    try:
        autor = denuncia.user.username if denuncia.user else 'usuário removido'
        mensagem = f'{denuncia.get_tipo_display()} enviada por {autor}'
        if denuncia.occurrence:
            mensagem += f' sobre a ocorrência "{denuncia.occurrence.title}"'
        mensagem += f': {denuncia.descricao[:120]}'
        if len(denuncia.descricao) > 120:
            mensagem += '…'

        notificadas = []
        for admin in _destinatarios_admin():
            if denuncia.user_id and admin.id == denuncia.user_id:
                continue  # o admin que abriu a denúncia não precisa ser avisado dela
            n = FACTORIES['push'].notificar(
                admin, f'{TITULO_NOVA_DENUNCIA} #{denuncia.id}', mensagem,
                occurrence=denuncia.occurrence, tipo='geral',
            )
            notificadas.append(n.id)
        return notificadas
    except Exception as e:
        print(f'[notificar_nova_denuncia] Falha ao avisar administradores: {e}')
        return []
