"""Observadores dos eventos da ocorrência (padrão Observer — ver `events.py`)."""
from occurrences.events import (
    OCORRENCIA_CRIADA, OCORRENCIA_DESIGNADA, OCORRENCIA_TRIADA, STATUS_ALTERADO, Observer, eventos,
)
from users.perfis import is_admin


class NotificacaoObserver(Observer):
    """Traduz cada evento no aviso do sino correspondente (notifications/services.py)."""

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
        elif evento.nome == OCORRENCIA_DESIGNADA:
            services.notificar_designacao(occ, evento.dados['pessoa'], evento.por)
        elif evento.nome == STATUS_ALTERADO:
            services.notificar_status_alterado(occ, evento.dados.get('anterior'), evento.por)


def registrar() -> None:
    observador = NotificacaoObserver()
    for nome in (OCORRENCIA_CRIADA, OCORRENCIA_TRIADA, OCORRENCIA_DESIGNADA, STATUS_ALTERADO):
        eventos.inscrever(nome, observador)
