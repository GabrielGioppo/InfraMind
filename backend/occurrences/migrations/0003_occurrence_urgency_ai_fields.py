from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrences', '0002_occurrence_importance_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='urgency_level',
            field=models.CharField(
                choices=[('critica', 'Crítica'), ('alta', 'Alta'), ('media', 'Média'), ('baixa', 'Baixa')],
                default='baixa',
                max_length=10,
                verbose_name='Urgência (IA)',
                help_text='Classificado automaticamente pelo Gemini com base no conteúdo',
            ),
        ),
        migrations.AddField(
            model_name='occurrence',
            name='urgency_score',
            field=models.IntegerField(default=0, verbose_name='Score de Urgência (0-100)'),
        ),
        migrations.AddField(
            model_name='occurrence',
            name='urgency_keywords',
            field=models.JSONField(blank=True, default=list, verbose_name='Palavras-chave de risco encontradas'),
        ),
        migrations.AddField(
            model_name='occurrence',
            name='urgency_reason',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Motivo da classificação de urgência'),
        ),
        migrations.AddField(
            model_name='occurrence',
            name='ai_duplicate_checked',
            field=models.BooleanField(default=False, verbose_name='Verificação de duplicata realizada pela IA'),
        ),
        migrations.AddField(
            model_name='occurrence',
            name='ai_duplicate_confidence',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Confiança da verificação de duplicata'),
        ),
    ]
