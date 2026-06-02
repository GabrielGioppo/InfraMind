import os
from dotenv import load_dotenv
from django.db.models.signals import pre_save
from django.dispatch import receiver
from gemini_api.client import get_occurrence_ai_suggestion
from occurrences.models import Occurrence

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY', '')


@receiver(pre_save, sender=Occurrence)
def occurrence_pre_save(sender, instance, **kwargs):
    """
    Antes de salvar uma ocorrência nova sem descrição,
    sugere uma descrição via Gemini com base no título e categoria.
    """
    if not instance.pk and not instance.description:
        if len(api_key) > 0:
            category_name = instance.category.name if instance.category else 'Geral'
            ai_suggestion = get_occurrence_ai_suggestion(instance.title, category_name)
            instance.description = ai_suggestion