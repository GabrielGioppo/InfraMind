from occurrences.events import (
    FEEDBACK_REGISTRADO, OCORRENCIA_ATUALIZADA, OCORRENCIA_CRIADA, OCORRENCIA_DESIGNADA, OCORRENCIA_TRIADA,
    STATUS_ALTERADO, TRIAGEM_REJEITADA, Observer, eventos,
)
from users.perfis import is_admin


class NotificacaoObserver(Observer):

    def atualizar(self, evento):
        from notifications import services
        occ = evento.ocorrencia
        if evento.nome == OCORRENCIA_CRIADA:
            services.notificar_nova_ocorrencia(occ)
        elif evento.nome == OCORRENCIA_TRIADA:
            antes = evento.dados.get('setor_anterior_id')
            # Avisa o setor de destino quando a triagem veio de fora dele (admin ou outro setor).
            if is_admin(evento.por) or occ.category_id != antes:
                services.notificar_encaminhamento(occ, evento.por)
            services.notificar_cidadao(
                occ, evento.por, f'Sua ocorrência foi aprovada — #{occ.id}',
                f'"{occ.title}" passou pela triagem e foi encaminhada ao setor '
                f'{occ.category.name if occ.category else "responsável"}.')
        elif evento.nome == TRIAGEM_REJEITADA:
            services.notificar_cidadao(
                occ, evento.por, f'Sua ocorrência não foi aceita — #{occ.id}',
                f'"{occ.title}" foi encerrada na triagem. Motivo: {evento.dados.get("motivo") or "não informado"}.')
        elif evento.nome == OCORRENCIA_DESIGNADA:
            services.notificar_designacao(occ, evento.dados['pessoa'], evento.por)
            services.notificar_cidadao(
                occ, evento.por, f'Equipe designada — #{occ.id}',
                f'Uma equipe técnica foi designada para atender "{occ.title}".')
        elif evento.nome == STATUS_ALTERADO:
            services.notificar_status_alterado(occ, evento.dados.get('anterior'), evento.por)
        elif evento.nome == OCORRENCIA_ATUALIZADA:
            services.notificar_cidadao(
                occ, evento.por, f'Atualização na sua ocorrência — #{occ.id}',
                f'"{occ.title}": ' + '; '.join(evento.dados['mudancas']) + '.')
        elif evento.nome == FEEDBACK_REGISTRADO:
            services.notificar_feedback(evento.dados['feedback'], evento.por)


def registrar() -> None:
    observador = NotificacaoObserver()
    for nome in (OCORRENCIA_CRIADA, OCORRENCIA_TRIADA, TRIAGEM_REJEITADA, OCORRENCIA_DESIGNADA, STATUS_ALTERADO,
                 OCORRENCIA_ATUALIZADA, FEEDBACK_REGISTRADO):
        eventos.inscrever(nome, observador)
