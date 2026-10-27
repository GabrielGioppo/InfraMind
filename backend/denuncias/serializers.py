from rest_framework import serializers

from denuncias.models import Denuncia
from occurrences.visibility import visible_occurrences

DESCRICAO_MIN = 10
DESCRICAO_MAX = 2000


class DenunciaSerializer(serializers.ModelSerializer):
    """Criação e leitura pelo cidadão. O status só muda pelo administrador."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    occurrence_title = serializers.CharField(source='occurrence.title', read_only=True, default=None)
    autor = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = Denuncia
        fields = ['id', 'tipo', 'tipo_display', 'descricao', 'occurrence', 'occurrence_title',
                  'status', 'status_display', 'autor', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_descricao(self, value):
        value = (value or '').strip()
        if len(value) < DESCRICAO_MIN:
            raise serializers.ValidationError(f'Descreva com pelo menos {DESCRICAO_MIN} caracteres.')
        if len(value) > DESCRICAO_MAX:
            raise serializers.ValidationError(f'Máximo de {DESCRICAO_MAX} caracteres.')
        return value

    def validate(self, attrs):
        tipo = attrs.get('tipo')
        occurrence = attrs.get('occurrence')
        if tipo == 'conteudo_inadequado' and occurrence is None:
            raise serializers.ValidationError(
                {'occurrence': 'Informe a ocorrência que contém o conteúdo denunciado.'}
            )
        if occurrence is not None:
            user = self.context['request'].user
            if not visible_occurrences(user).filter(pk=occurrence.pk).exists():
                raise serializers.ValidationError({'occurrence': 'Ocorrência não encontrada.'})
        return attrs


class DenunciaStatusSerializer(serializers.ModelSerializer):
    """Uso do administrador: altera apenas o status."""

    class Meta:
        model = Denuncia
        fields = ['id', 'status']
