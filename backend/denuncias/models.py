from django.db import models

from occurrences.models import Occurrence
from users.models import User


class Denuncia(models.Model):
    """UC-13 — denúncia de conteúdo inadequado ou relato de problema técnico (suporte)."""

    TIPO_CHOICES = [
        ('bug', 'Problema técnico (bug)'),
        ('conteudo_inadequado', 'Conteúdo inadequado'),
    ]
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('em_analise', 'Em análise'),
        ('resolvida', 'Resolvida'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='denuncias',
    )
    # Obrigatória em "conteúdo inadequado" (qual ocorrência está sendo denunciada).
    occurrence = models.ForeignKey(
        Occurrence, on_delete=models.SET_NULL, null=True, blank=True, related_name='denuncias',
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='aberta')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_tipo_display()} #{self.pk} ({self.get_status_display()})'
