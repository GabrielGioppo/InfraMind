from django.utils import timezone
from rest_framework import serializers
from categories.models import Category, Subcategory
from occurrences.models import Occurrence
from users.serializers import UserSerializer
from categories.serializers import CategoriaResumoSerializer, SubcategorySerializer
from images.serializers import ImageSerializer
from feedbacks.serializers import FeedbackSerializer
from occurrences.sla import prazo_final, sla_status

HORARIO_PADRAO_PRAZO = 'T23:59:59'


# Campos gerados pela IA — visíveis apenas para admins
AI_FIELDS = [
    'urgency_level', 'urgency_score', 'urgency_keywords', 'urgency_reason',
    'ai_duplicate_checked', 'ai_duplicate_confidence',
]


class PrazoDateTimeField(serializers.DateTimeField):
    """
    Aceita 'AAAA-MM-DDTHH:MM' (data e hora) ou só 'AAAA-MM-DD'. Sem horário, assume 23:59:59.
    Horários sem fuso são interpretados no fuso do projeto (America/Sao_Paulo).
    """
    def to_internal_value(self, value):
        if isinstance(value, str):
            value = value.strip()
            if len(value) == 10 and value[4] == '-' and value[7] == '-':
                value += HORARIO_PADRAO_PRAZO
        return super().to_internal_value(value)


class SlaFieldsMixin(serializers.Serializer):
    """Indicador de prazo (UC-14, passo 4) — calculado na leitura, sempre atualizado."""
    sla_deadline = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()

    def get_sla_deadline(self, obj):
        limite = prazo_final(obj)
        return limite.isoformat() if limite else None

    def get_sla_status(self, obj):
        return sla_status(obj)


class SubcategoriaMixin:
    """O setor e a subcategoria precisam combinar. Informar só a subcategoria já define o setor;
    trocar só o setor numa edição limpa a subcategoria que ficou de outro setor."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        atual = self.instance
        categoria = attrs['category'] if 'category' in attrs else getattr(atual, 'category', None)
        if 'subcategory' in attrs:
            sub = attrs['subcategory']
            if sub is not None:
                if categoria is None:
                    attrs['category'] = sub.category
                elif sub.category_id != categoria.pk:
                    raise serializers.ValidationError(
                        {'subcategory': 'Essa subcategoria não pertence ao setor escolhido.'})
        elif 'category' in attrs:
            sub = getattr(atual, 'subcategory', None)
            if sub is not None and (categoria is None or sub.category_id != categoria.pk):
                attrs['subcategory'] = None
        return attrs


class OccurrenceSerializer(SubcategoriaMixin, SlaFieldsMixin, serializers.ModelSerializer):
    """Serializer para usuários comuns — inclui status e sugestões da análise de IA da descrição"""
    user_details = UserSerializer(source='user', read_only=True)
    category_details = CategoriaResumoSerializer(source='category', read_only=True)
    subcategory_details = SubcategorySerializer(source='subcategory', read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    feedbacks = FeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = Occurrence
        exclude = AI_FIELDS
        read_only_fields = ['user', 'validation_count', 'priority', 'is_duplicate', 'importance_color',
                            'prazo_definido', 'triagem', 'triagem_em', 'triagem_por', 'triagem_obs',
                            'gestor_responsavel', 'equipe_responsavel', 'parecer_encerramento']


class OccurrenceAdminSerializer(SubcategoriaMixin, SlaFieldsMixin, serializers.ModelSerializer):
    """Serializer exclusivo para admins — permite editar importance_color e ver análise da IA"""
    prazo_definido = PrazoDateTimeField(required=False, allow_null=True)
    user_details = UserSerializer(source='user', read_only=True)
    category_details = CategoriaResumoSerializer(source='category', read_only=True)
    subcategory_details = SubcategorySerializer(source='subcategory', read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    feedbacks = FeedbackSerializer(many=True, read_only=True)

    triagem_por_nome = serializers.SerializerMethodField()
    gestor_responsavel_nome = serializers.SerializerMethodField()
    equipe_responsavel_nome = serializers.SerializerMethodField()

    class Meta:
        model = Occurrence
        fields = '__all__'
        # A triagem e a designação só mudam pelos endpoints próprios
        # (POST /occurrences/<id>/triagem/ e /designar/).
        read_only_fields = ['user', 'validation_count', 'priority', 'is_duplicate',
                            'triagem', 'triagem_em', 'triagem_por', 'triagem_obs',
                            'gestor_responsavel', 'equipe_responsavel']

    def get_gestor_responsavel_nome(self, obj):
        return obj.gestor_responsavel.username if obj.gestor_responsavel_id else None

    def get_equipe_responsavel_nome(self, obj):
        return obj.equipe_responsavel.username if obj.equipe_responsavel_id else None

    def get_triagem_por_nome(self, obj):
        return obj.triagem_por.username if obj.triagem_por_id else None


class OccurrenceEquipeSerializer(OccurrenceAdminSerializer):
    """Equipe técnica: vê tudo da sua área, mas só altera o status e o parecer do atendimento."""

    def get_fields(self):
        campos = super().get_fields()
        for nome, campo in campos.items():
            if nome not in ('status', 'parecer_encerramento'):
                campo.read_only = True
        return campos


class AnonOccurrenceSerializer(SubcategoriaMixin, serializers.ModelSerializer):
    """Serializer para criação anônima — não exige user, aceita anon_id"""

    class Meta:
        model = Occurrence
        fields = [
            'id', 'title', 'description', 'category', 'subcategory', 'address', 'city', 'state',
            'latitude', 'longitude', 'status', 'anon_id', 'created_at',
            'original_description', 'description_analysis_status', 'description_suggestion',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class TriagemSerializer(serializers.Serializer):
    """
    Entrada do POST /occurrences/<id>/triagem/.

    aprovar:  importância + prazo (ficam os que a ocorrência já tem, se não vierem) e,
              opcionalmente, o setor/subcategoria responsável (encaminhamento).
    rejeitar: exige o motivo em `observacao` (ex.: conteúdo falso ou fora do escopo).
    """
    acao = serializers.ChoiceField(choices=['aprovar', 'rejeitar'], default='aprovar')
    importance_color = serializers.ChoiceField(choices=[c[0] for c in Occurrence.IMPORTANCE_CHOICES], required=False)
    prazo_definido = PrazoDateTimeField(required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    subcategory = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.all(), required=False, allow_null=True)
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        occ = self.context['occurrence']
        if attrs['acao'] == 'rejeitar':
            if not (attrs.get('observacao') or '').strip():
                raise serializers.ValidationError({'observacao': 'Informe o motivo da rejeição.'})
            return attrs

        erros = {}
        if not (attrs.get('importance_color') or occ.importance_color):
            erros['importance_color'] = 'Defina o nível de importância.'
        prazo = attrs.get('prazo_definido') or occ.prazo_definido
        if not prazo:
            erros['prazo_definido'] = 'Defina o prazo para resolver.'
        elif 'prazo_definido' in attrs and prazo <= timezone.now():
            erros['prazo_definido'] = 'O prazo precisa estar no futuro.'
        if erros:
            raise serializers.ValidationError(erros)

        # Setor e subcategoria precisam combinar (mesma regra do cadastro/edição).
        sub = attrs.get('subcategory')
        categoria = attrs.get('category') or occ.category
        if sub is not None:
            if 'category' not in attrs and occ.category_id is None:
                attrs['category'] = sub.category
            elif sub.category_id != (categoria.pk if categoria else None):
                raise serializers.ValidationError({'subcategory': 'Essa subcategoria não pertence ao setor escolhido.'})
        return attrs

