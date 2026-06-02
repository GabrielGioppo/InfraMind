import os
from dotenv import load_dotenv
from django.db.models.signals import pre_save
from django.dispatch import receiver
from gemini_api.client import get_category_ai_description
from categories.models import Category

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY', '')


@receiver(pre_save, sender=Category)
def category_pre_save(sender, instance, **kwargs):
    """
    Antes de salvar uma categoria, se ela não tiver descrição,
    gera automaticamente via Gemini — mesmo padrão da Aula 10.
    """
    if not instance.description:
        if len(api_key) > 0:
            ai_description = get_category_ai_description(instance.name)
            instance.description = ai_description
