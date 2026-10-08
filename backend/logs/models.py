from django.db import models
from users.models import User


class Log(models.Model):
    """Model para logs do sistema (RF28 / RNF14)."""

    ACTION_CHOICES = [
        ('create', 'Criar'),
        ('update', 'Atualizar'),
        ('delete', 'Deletar'),
        ('validate', 'Validar'),
        ('status_change', 'Mudança de Status'),
        ('login', 'Login'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.IntegerField()
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} — {self.action} — {self.model_name}'
