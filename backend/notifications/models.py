from django.db import models
from users.models import User
from occurrences.models import Occurrence


class Notificacao(models.Model):
    """
    Notificacao — Produto do Factory Method (notifications/factory.py)

    Instanciada e enviada pelas fábricas concretas EmailNotifFactory e
    PushNotifFactory, de acordo com o canal escolhido. Também é a
    entidade persistida quando o UC-14 (Processar Prazos e Disparar
    Notificações) dispara um aviso de prazo estourado.
    """

    CANAL_CHOICES = [
        ('email', 'E-mail'),
        ('push', 'Push'),
    ]

    TIPO_CHOICES = [
        ('prazo_estourado', 'Prazo Estourado'),
        ('status_change', 'Mudança de Status'),
        ('geral', 'Geral'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviada', 'Enviada'),
        ('falha', 'Falha no Envio'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificacoes',
    )
    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notificacoes',
    )

    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='geral')

    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_canal_display()} para {self.user} — {self.titulo} [{self.status}]'
