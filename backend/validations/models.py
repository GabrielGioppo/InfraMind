from django.db import models
from users.models import User
from occurrences.models import Occurrence

class Validation(models.Model):
    """Model para validações de ocorrências"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='validations'
    )
    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='validations'
    )
    validated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'occurrence']  # Um usuário valida apenas uma vez
    
    def __str__(self):
        return f"{self.user.username} validou {self.occurrence.title}"