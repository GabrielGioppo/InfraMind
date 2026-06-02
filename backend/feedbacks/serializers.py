from rest_framework import serializers
from feedbacks.models import Feedback
from users.serializers import UserSerializer


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer base — usuários comuns podem enviar feedback com nota"""
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class AdminFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer para admins — apenas comentário/atualização do ocorrido.
    Admins NÃO podem enviar nota (rating) nem resolved.
    """
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Feedback
        # Admins só postam comentário e vinculam à ocorrência
        fields = ['id', 'user', 'user_details', 'occurrence', 'comment', 'created_at']
        read_only_fields = ['user', 'created_at']

    def validate(self, data):
        # Garante que rating e resolved não sejam enviados por admins
        if 'rating' in self.initial_data:
            raise serializers.ValidationError(
                "Administradores não podem enviar notas (rating). "
                "Use este endpoint apenas para atualizações do ocorrido."
            )
        return data
