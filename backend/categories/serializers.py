from rest_framework import serializers
from categories.models import Category, Subcategory


def _e_admin(request):
    u = getattr(request, 'user', None)
    return bool(u and u.is_authenticated and (u.user_type == 'admin' or u.is_staff))


class SubcategorySerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_blank=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Subcategory
        fields = ['id', 'category', 'category_name', 'name', 'description', 'is_active', 'created_at']
        read_only_fields = ['created_at']
        validators = []  # a unicidade (setor + nome) é tratada em validate()

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Informe o nome da subcategoria.')
        return value

    def validate(self, attrs):
        category = attrs.get('category') or getattr(self.instance, 'category', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if category and name:
            dup = Subcategory.objects.filter(category=category, name__iexact=name)
            if self.instance:
                dup = dup.exclude(pk=self.instance.pk)
            if dup.exists():
                raise serializers.ValidationError({'name': 'Esse setor já tem uma subcategoria com esse nome.'})
        return attrs


class CategorySerializer(serializers.ModelSerializer):
    # Declarar o campo explicitamente aqui quebra qualquer validação automática rígida do DRF
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # Cidadão e visitante veem só as subcategorias ativas; o administrador vê todas.
    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = '__all__'

    def get_subcategories(self, obj):
        qs = obj.subcategories.all()
        if not _e_admin(self.context.get('request')):
            qs = qs.filter(is_active=True)
        return SubcategorySerializer(qs, many=True).data

    # Força o Django a transformar qualquer string vazia ou erro em None (null) antes de salvar
    def validate_description(self, value):
        if value == "" or value is None:
            return None
        return value


class CategoriaResumoSerializer(serializers.ModelSerializer):
    """Versão enxuta (sem a lista de subcategorias) para embutir em ocorrências."""
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'is_active']
