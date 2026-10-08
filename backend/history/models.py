from django.db import models
from users.models import User
from occurrences.models import Occurrence


class OccurrenceHistory(models.Model):
    """
    Rastreia todas as alterações de status das ocorrências (RF27).
    """
    CHANGE_TYPES = [
        ('status', 'Mudança de Status'),
        ('priority', 'Mudança de Prioridade'),
        ('edit', 'Edição de Dados'),
    ]

    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='history'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='occurrence_history'
    )
    previous_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20, blank=True, null=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES, default='status')
    observation = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.occurrence.title} | {self.previous_status} → {self.new_status}'
