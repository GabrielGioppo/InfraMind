from rest_framework import serializers
from notifications.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = [
            'id', 'occurrence', 'canal', 'tipo',
            'titulo', 'mensagem', 'status',
            'created_at', 'sent_at',
        ]
        read_only_fields = fields
