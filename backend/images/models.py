from django.db import models
from occurrences.models import Occurrence
from users.models import User

class Image(models.Model):
    """Model para imagens das ocorrências"""

    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='images'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='images'
    )
    image = models.ImageField(upload_to='occurrences/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Imagem da ocorrência: {self.occurrence.title}"
