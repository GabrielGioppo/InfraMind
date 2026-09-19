from django.db import models
from users.models import User
from categories.models import Category


class Occurrence(models.Model):
    """Model principal para ocorrências"""

    STATUS_CHOICES = [
        ('open', 'Aberta'),
        ('in_progress', 'Em Andamento'),
        ('resolved', 'Resolvida'),
        ('closed', 'Fechada'),
    ]

    IMPORTANCE_CHOICES = [
        ('green', 'Normal'),
        ('yellow', 'Um Pouco Importante'),
        ('red', 'Importante'),
    ]

    URGENCY_CHOICES = [
        ('critica', 'Crítica'),
        ('alta', 'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
    ]

    # Relacionamentos
    user = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='occurrences',
        null=True,
        blank=True,
    )

    # Identificador anônimo — gerado no browser, usado para vincular ao fazer login
    anon_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name='occurrences',
        null=True,
        blank=True
    )

    # Dados da ocorrência
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')  # opcional
    latitude  = models.DecimalField(max_digits=100, decimal_places=20, null=True, blank=True)
    longitude = models.DecimalField(max_digits=100, decimal_places=20, null=True, blank=True)
    address = models.TextField(blank=True, null=True)

    # Status e controle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.IntegerField(default=0)
    estimated_time = models.IntegerField(null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates'
    )

    # Importância — definida pelo admin após análise
    importance_color = models.CharField(
        max_length=10,
        choices=IMPORTANCE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Nível de Importância',
        help_text='Verde = Normal | Amarelo = Um pouco importante | Vermelho = Importante'
    )

    # Urgência — classificada automaticamente pelo Gemini (RF23)
    urgency_level = models.CharField(
        max_length=10,
        choices=URGENCY_CHOICES,
        default='baixa',
        verbose_name='Urgência (IA)',
        help_text='Classificado automaticamente pelo Gemini com base no conteúdo'
    )
    urgency_score = models.IntegerField(
        default=0,
        verbose_name='Score de Urgência (0-100)',
    )
    urgency_keywords = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Palavras-chave de risco encontradas',
    )
    urgency_reason = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Motivo da classificação de urgência',
    )

    # Duplicata — verificada automaticamente pelo Gemini
    ai_duplicate_checked = models.BooleanField(
        default=False,
        verbose_name='Verificação de duplicata realizada pela IA',
    )
    ai_duplicate_confidence = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name='Confiança da verificação de duplicata',
    )

    # Datas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Validações
    validation_count = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.title} — {self.status} [{self.urgency_level}]'