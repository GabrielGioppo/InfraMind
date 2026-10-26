from rest_framework import serializers
from notifications.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    occurrence_title = serializers.CharField(source='occurrence.title', read_only=True, default=None)

    class Meta:
        model = Notificacao
        fields = '__all__'
        read_only_fields = [
            'user', 'occurrence', 'canal', 'tipo', 'titulo',
            'mensagem', 'status', 'created_at', 'sent_at',
        ]
