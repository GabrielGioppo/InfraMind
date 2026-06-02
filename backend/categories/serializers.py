from rest_framework import serializers
from categories.models import Category

class CategorySerializer(serializers.ModelSerializer):
    # Declarar o campo explicitamente aqui quebra qualquer validação automática rígida do DRF
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Category
        fields = '__all__'

    # Força o Django a transformar qualquer string vazia ou erro em None (null) antes de salvar
    def validate_description(self, value):
        if value == "" or value is None:
            return None
        return value