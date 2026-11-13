from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from notifications.factory import EmailNotifFactory, PushNotifFactory
from notifications.models import Notificacao
from occurrences.models import Occurrence
from occurrences.sla import LIMIAR_AVISO_PREVENTIVO, STATUS_ENCERRADOS, prazo_final
from history.models import OccurrenceHistory
from users.validators import chave_cidade

User = get_user_model()

TIPO_PRAZO_ESTOURADO = 'prazo_estourado'
TIPO_AVISO_PRAZO     = 'aviso_prazo'
TIPO_STATUS_CHANGE   = 'status_change'

# Título dos avisos de suporte; o painel admin usa o prefixo para abrir a aba Suporte.
TITULO_NOVA_DENUNCIA = 'Novo chamado de suporte'

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
    Administradores recebem todos os avisos de prazo. O gestor do setor/cidade e a equipe
    designada também recebem os da ocorrência deles (ver `_responsaveis`).
    """
    return list(User.objects.filter(Q(is_staff=True) | Q(user_type='admin')).distinct())


def gestores_da_area(occ) -> list:
    """Gestores públicos do setor e da cidade da ocorrência."""
    if not (occ.category_id and occ.city_key and occ.state):
        return []
    candidatos = User.objects.filter(
        user_type='gestor', setor_id=occ.category_id, uf__iexact=occ.state, is_active=True)
    return [u for u in candidatos if chave_cidade(u.cidade) == occ.city_key]


def _responsaveis(occ) -> list:
    """Quem responde pela ocorrência: gestores da área + gestor e equipe designados."""
    pessoas = list(gestores_da_area(occ))
    pessoas += [u for u in (occ.gestor_responsavel, occ.equipe_responsavel) if u]
    return pessoas


def _sem_repetir(pessoas) -> list:
    return list({u.id: u for u in pessoas}.values())


def _avisar(pessoas, titulo, mensagem, occ, tipo) -> list:
    """Aviso no sino (push) para cada pessoa. Nunca levanta exceção: o aviso não pode derrubar a ação principal."""
    ids = []
    for pessoa in _sem_repetir(pessoas):
        try:
            ids.append(FACTORIES['push'].notificar(pessoa, titulo, mensagem, occurrence=occ, tipo=tipo).id)
        except Exception as e:
            print(f'[notificacoes] Falha ao avisar {pessoa.pk} ({tipo}): {e}')
    return ids


def notificar_nova_ocorrencia(occ) -> list:
    """Chegou uma ocorrência nova: avisa os gestores do setor e da cidade, que fazem a triagem."""
    destinatarios = [g for g in gestores_da_area(occ) if g.id != occ.user_id]
    return _avisar(destinatarios, f'Nova ocorrência para triagem — #{occ.id}',
                   f'"{occ.title}" ({occ.category.name if occ.category else "sem setor"}) aguarda triagem.',
                   occ, 'nova_ocorrencia')


def notificar_encaminhamento(occ, por) -> list:
    """A triagem aprovou/encaminhou a ocorrência: avisa os gestores do setor responsável (menos quem triou)."""
    destinatarios = [g for g in gestores_da_area(occ) if not por or g.id != por.id]
    return _avisar(destinatarios, f'Ocorrência encaminhada ao seu setor — #{occ.id}',
                   f'"{occ.title}" foi triada e encaminhada para {occ.category.name if occ.category else "o setor"}.',
                   occ, 'encaminhamento')


def notificar_designacao(occ, pessoa, por) -> list:
    """Avisa a pessoa que recebeu a ocorrência."""
    quem = f' por {por.username}' if por else ''
    return _avisar([pessoa], f'Ocorrência designada para você — #{occ.id}',
                   f'"{occ.title}" foi designada{quem}. Prazo: {_descrever_prazo(occ) if (occ.prazo_definido or occ.estimated_time) else "não definido"}.',
                   occ, 'designacao')


_ROTULO_STATUS = dict(Occurrence.STATUS_CHOICES)


def notificar_status_alterado(occ, anterior, por) -> list:
    """Mudou o status: avisa quem responde pela ocorrência (menos quem mudou). O cidadão é avisado pela rotina UC-14."""
    destinatarios = [p for p in _responsaveis(occ) if not por or p.id != por.id]
    quem = f' por {por.username}' if por else ''
    return _avisar(destinatarios, f'Status alterado — #{occ.id}',
                   f'"{occ.title}": {_ROTULO_STATUS.get(anterior, anterior or "—")} → {_ROTULO_STATUS.get(occ.status, occ.status)}{quem}.',
                   occ, TIPO_STATUS_CHANGE)


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
        destinatarios = _sem_repetir(admins + _responsaveis(occ) + ([occ.user] if occ.user else []))
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
        for destinatario in _sem_repetir(admins + _responsaveis(occ)):
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
