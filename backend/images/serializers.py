from rest_framework import serializers
from images.models import Image
from occurrences.visibility import visible_occurrences
from users.perfis import is_admin, is_equipe, is_municipal

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'
        read_only_fields = ['user', 'uploaded_at']

    def validate(self, attrs):
        # Foto da resolução (evidência do encerramento): só quem atende a ocorrência envia.
        if attrs.get('etapa') == 'resolucao':
            request = self.context.get('request')
            user = getattr(request, 'user', None)
            occ = attrs.get('occurrence')
            if not (user and user.is_authenticated and (is_admin(user) or is_municipal(user))):
                raise serializers.ValidationError({'etapa': 'Só administrador, gestor e equipe técnica enviam a evidência da resolução.'})
            if not visible_occurrences(user).filter(pk=occ.pk).exists():
                raise serializers.ValidationError({'occurrence': 'Esta ocorrência não é da sua área.'})
            if is_equipe(user) and occ.equipe_responsavel_id != user.id:
                raise serializers.ValidationError({'occurrence': 'Esta ocorrência não foi designada para você.'})
        return attrs
