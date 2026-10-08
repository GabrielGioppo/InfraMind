from django.db import models
from users.models import User
from occurrences.models import Occurrence


class Notificacao(models.Model):
    """Model de notificação (UC-14) — criada pelas fábricas em factory.py."""

    CANAL_CHOICES = [
        ('email', 'E-mail'),
        ('push', 'Push'),
    ]
    TIPO_CHOICES = [
        ('prazo_estourado', 'Prazo Estourado'),
        ('aviso_prazo', 'Aviso de Proximidade de Prazo'),
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
        related_name='notificacoes',
        null=True,
        blank=True,
    )
    canal   = models.CharField(max_length=10, choices=CANAL_CHOICES)
    tipo    = models.CharField(max_length=20, choices=TIPO_CHOICES, default='geral')
    titulo  = models.CharField(max_length=200)
    mensagem = models.TextField()
    status  = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendente')
    read    = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.canal}] {self.get_tipo_display()} → {self.user.username} ({self.status})'
