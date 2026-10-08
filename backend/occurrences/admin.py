from django.contrib import admin
from occurrences.models import Occurrence


class OccurrenceAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'category', 'status',
        'urgency_level', 'urgency_score', 'priority',
        'importance_color', 'is_duplicate', 'created_at',
    )
    search_fields = ('title', 'description', 'address')
    list_filter = ('status', 'urgency_level', 'importance_color', 'category', 'is_duplicate')

    # Ordenação padrão: urgência crítica primeiro, depois score, depois prioridade
    ordering = (
        models.Case(
            models.When(urgency_level='critica', then=0),
            models.When(urgency_level='alta',    then=1),
            models.When(urgency_level='media',   then=2),
            models.When(urgency_level='baixa',   then=3),
            default=4,
            output_field=models.IntegerField(),
        ),
        '-urgency_score',
        '-priority',
    ) if False else ('-urgency_score', '-priority')  # simplificado para evitar import circular

    list_editable = ('importance_color',)

    fieldsets = (
        ('Dados da Ocorrência', {
            'fields': ('title', 'description', 'category', 'user', 'address', 'latitude', 'longitude')
        }),
        ('Status e Controle', {
            'fields': ('status', 'priority', 'estimated_time', 'is_duplicate', 'duplicate_of', 'resolved_at')
        }),
        ('Análise do Administrador', {
            'fields': ('importance_color',),
            'description': 'Verde = Normal | Amarelo = Um pouco importante | Vermelho = Importante',
        }),
        ('Classificação por IA (Gemini)', {
            'fields': ('urgency_level', 'urgency_score', 'urgency_keywords', 'urgency_reason',
                       'ai_duplicate_checked', 'ai_duplicate_confidence'),
            'description': 'Campos preenchidos automaticamente pela análise do Gemini.',
        }),
    )

    readonly_fields = (
        'validation_count', 'created_at', 'updated_at',
        'urgency_level', 'urgency_score', 'urgency_keywords', 'urgency_reason',
        'ai_duplicate_checked', 'ai_duplicate_confidence',
    )


admin.site.register(Occurrence, OccurrenceAdmin)
