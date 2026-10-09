from rest_framework import serializers
from occurrences.models import Occurrence
from users.serializers import UserSerializer
from categories.serializers import CategorySerializer
from images.serializers import ImageSerializer
from feedbacks.serializers import FeedbackSerializer
from occurrences.sla import prazo_final, sla_status


# Campos gerados pela IA — visíveis apenas para admins
AI_FIELDS = [
    'urgency_level', 'urgency_score', 'urgency_keywords', 'urgency_reason',
    'ai_duplicate_checked', 'ai_duplicate_confidence',
]


class SlaFieldsMixin(serializers.Serializer):
    """Indicador de prazo (UC-14, passo 4) — calculado na leitura, sempre atualizado."""
    sla_deadline = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()

    def get_sla_deadline(self, obj):
        limite = prazo_final(obj)
        return limite.isoformat() if limite else None

    def get_sla_status(self, obj):
        return sla_status(obj)


class OccurrenceSerializer(SlaFieldsMixin, serializers.ModelSerializer):
    """Serializer para usuários comuns — campos de IA ocultados"""
    user_details = UserSerializer(source='user', read_only=True)
    category_details = CategorySerializer(source='category', read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    feedbacks = FeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = Occurrence
        exclude = AI_FIELDS
        read_only_fields = ['user', 'validation_count', 'priority', 'is_duplicate', 'importance_color']


class OccurrenceAdminSerializer(SlaFieldsMixin, serializers.ModelSerializer):
    """Serializer exclusivo para admins — permite editar importance_color e ver análise da IA"""
    user_details = UserSerializer(source='user', read_only=True)
    category_details = CategorySerializer(source='category', read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    feedbacks = FeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = Occurrence
        fields = '__all__'
        read_only_fields = ['user', 'validation_count', 'priority', 'is_duplicate']


class AnonOccurrenceSerializer(serializers.ModelSerializer):
    """Serializer para criação anônima — não exige user, aceita anon_id"""

    class Meta:
        model = Occurrence
        fields = [
            'id', 'title', 'description', 'category', 'address',
            'latitude', 'longitude', 'status', 'anon_id', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']
