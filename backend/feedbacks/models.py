from django.db import models
from users.models import User
from occurrences.models import Occurrence


class Feedback(models.Model):
    """
    Model para feedbacks e atualizações de ocorrências.

    - Cidadãos: enviam comentário + nota (rating) após resolução
    - Admins: enviam apenas atualizações do ocorrido (sem rating)
    """

    user = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='feedbacks'
    )
    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    comment = models.TextField()

    # Nota: obrigatória para cidadãos, nula para atualizações de admin
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        null=True,
        blank=True,
        help_text='Nota de 1 a 5. Obrigatória para cidadãos, não disponível para admins.'
    )

    resolved = models.BooleanField(default=False)
    real_resolution_time = models.IntegerField(null=True, blank=True)  # Tempo real em horas
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.rating:
            return f"Feedback de {self.user.username} - Nota: {self.rating}"
        return f"Atualização de {self.user.username} - {self.occurrence.title}"
