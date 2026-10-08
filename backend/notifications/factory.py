"""
Factory Method (Padrão Criacional) — notifications/factory.py

NotificacaoFactory define o "esqueleto" de criação + envio de uma
Notificacao (método `notificar`, um template method), delegando às
subclasses a decisão de QUAL canal instanciar — esse é o factory
method propriamente dito (`criar_notificacao`).

EmailNotifFactory e PushNotifFactory herdam de NotificacaoFactory e
sobrescrevem `criar_notificacao` (como configurar a Notificacao pro
canal) e `_enviar` (como efetivamente despachar nesse canal). Nenhuma
outra parte do sistema precisa saber como uma Notificacao por e-mail
difere de uma por push — só chama `factory.notificar(...)`.
"""

from abc import ABC, abstractmethod

from django.conf import settings
from django.utils import timezone

from notifications.models import Notificacao


class NotificacaoFactory(ABC):
    """Fábrica abstrata — ponto único de acesso ao disparo de notificações."""

    @abstractmethod
    def criar_notificacao(self, user, titulo: str, mensagem: str,
                           occurrence=None, tipo: str = 'geral') -> Notificacao:
        """Factory Method: instancia a Notificacao já configurada para o canal da subclasse."""
        raise NotImplementedError

    @abstractmethod
    def _enviar(self, notificacao: Notificacao) -> None:
        """Lógica de envio específica do canal (e-mail, push, etc.)."""
        raise NotImplementedError

    def notificar(self, user, titulo: str, mensagem: str,
                   occurrence=None, tipo: str = 'geral') -> Notificacao:
        """
        Template method: cria a notificação via factory method, persiste,
        dispara o envio no canal específico e atualiza o status conforme
        o resultado (enviada/falha).
        """
        notificacao = self.criar_notificacao(user, titulo, mensagem, occurrence, tipo)
        notificacao.save()

        try:
            self._enviar(notificacao)
            notificacao.status = 'enviada'
            notificacao.sent_at = timezone.now()
        except Exception as e:
            notificacao.status = 'falha'
            print(f'[{self.__class__.__name__}] Falha ao enviar notificação #{notificacao.id}: {e}')

        notificacao.save(update_fields=['status', 'sent_at'])
        return notificacao


class EmailNotifFactory(NotificacaoFactory):
    """Fábrica concreta — cria e envia notificações por e-mail."""

    def criar_notificacao(self, user, titulo, mensagem, occurrence=None, tipo='geral') -> Notificacao:
        return Notificacao(
            user=user,
            occurrence=occurrence,
            canal='email',
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
        )

    def _enviar(self, notificacao: Notificacao) -> None:
        from django.core.mail import send_mail

        destinatario = getattr(notificacao.user, 'email', None)
        if not destinatario:
            raise ValueError('Usuário sem e-mail cadastrado.')

        # Ambiente acadêmico sem SMTP configurado: 'localhost' é o default do
        # próprio Django quando EMAIL_HOST não foi definido em settings.py,
        # então tentar enviar de verdade só derrubaria a notificação em
        # 'falha' por falta de infraestrutura, não por erro de lógica. Loga
        # em vez disso; quando um SMTP real for configurado (settings com
        # EMAIL_HOST != 'localhost'), o envio passa a ser de verdade.
        email_host = getattr(settings, 'EMAIL_HOST', 'localhost')
        if not email_host or email_host == 'localhost':
            print(f'[EmailNotifFactory] (simulado) Para: {destinatario} | Assunto: {notificacao.titulo}')
            return

        send_mail(
            subject=notificacao.titulo,
            message=notificacao.mensagem,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@inframind.com'),
            recipient_list=[destinatario],
            fail_silently=False,
        )


class PushNotifFactory(NotificacaoFactory):
    """Fábrica concreta — cria e envia notificações push."""

    def criar_notificacao(self, user, titulo, mensagem, occurrence=None, tipo='geral') -> Notificacao:
        return Notificacao(
            user=user,
            occurrence=occurrence,
            canal='push',
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
        )

    def _enviar(self, notificacao: Notificacao) -> None:
        # TODO: integrar com um provedor real de push (ex.: Firebase Cloud Messaging).
        # Por ora, simula o envio via log — mantém o restante do sistema
        # (models, factory, UC-14) já pronto para quando a integração existir.
        print(f'[PushNotifFactory] (simulado) Push para {notificacao.user} | {notificacao.titulo}')
