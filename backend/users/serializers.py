from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from categories.models import Category
from users.perfis import PERFIS_MUNICIPAIS, is_admin, is_municipal
from users.validators import UFS, cpf_valido, somente_digitos

User = get_user_model()

# Dados pessoais: só o próprio usuário e administradores enxergam. Sem isso, o
# CPF e o endereço vazariam em qualquer lugar que embute o usuário (ex.: o autor
# de uma ocorrência) ou na listagem de usuários.
CAMPOS_SENSIVEIS = ('cpf', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf')


class UserSerializer(serializers.ModelSerializer):
    cpf = serializers.CharField(required=False, allow_null=True, allow_blank=True, validators=[])
    cep = serializers.CharField(required=False, allow_blank=True)
    uf = serializers.CharField(required=False, allow_blank=True)
    # Setor do gestor público / da equipe técnica (só o administrador define).
    setor = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True)
    setor_nome = serializers.SerializerMethodField()
    is_staff = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'setor', 'setor_nome', 'disponivel', 'is_staff', 'date_of_birth', 'phone', 'address',
                  'cpf', 'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf',
                  'is_active', 'created_at', 'updated_at', 'password']
        read_only_fields = ['is_active']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    # ── validações ────────────────────────────────────────────────
    def validate_cpf(self, value):
        if not value:
            return None
        cpf = somente_digitos(value)
        if not cpf_valido(cpf):
            raise serializers.ValidationError('CPF inválido.')
        outros = User.objects.filter(cpf=cpf)
        if self.instance is not None:
            outros = outros.exclude(pk=self.instance.pk)
        if outros.exists():
            raise serializers.ValidationError('Já existe um usuário com este CPF.')
        return cpf

    def validate_cep(self, value):
        cep = somente_digitos(value)
        if cep and len(cep) != 8:
            raise serializers.ValidationError('CEP deve ter 8 dígitos.')
        return cep

    def validate_uf(self, value):
        uf = (value or '').strip().upper()
        if uf and uf not in UFS:
            raise serializers.ValidationError('UF inválida.')
        return uf

    def get_setor_nome(self, obj):
        return obj.setor.name if obj.setor_id else None

    def _quem_pede(self):
        request = self.context.get('request')
        viewer = getattr(request, 'user', None)
        return viewer if (viewer and viewer.is_authenticated) else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        viewer = self._quem_pede()
        if not (viewer and is_admin(viewer)):
            # Só o administrador muda o perfil e o setor de alguém (evita se promover a admin/gestor).
            attrs.pop('user_type', None)
            attrs.pop('setor', None)
            # Gestor e equipe técnica têm a cidade definida pelo administrador.
            if self.instance is not None and is_municipal(self.instance):
                for campo in ('cidade', 'uf'):
                    if campo in attrs and attrs[campo] != getattr(self.instance, campo):
                        raise serializers.ValidationError(
                            {campo: 'A cidade de gestor e equipe técnica é definida pelo administrador.'})

        tipo = attrs.get('user_type', getattr(self.instance, 'user_type', None))
        if tipo in PERFIS_MUNICIPAIS:
            faltando = {}
            for campo in ('setor', 'cidade', 'uf'):
                valor = attrs[campo] if campo in attrs else getattr(self.instance, campo, None)
                if not valor:
                    faltando[campo] = 'Obrigatório para gestor público e equipe técnica.'
            if faltando:
                raise serializers.ValidationError(faltando)
        return attrs

    # ── escrita ───────────────────────────────────────────────────
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password and str(password).strip():
            instance.set_password(password)
        instance.save()
        return instance

    # ── leitura ───────────────────────────────────────────────────
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        viewer = getattr(request, 'user', None)
        pode_ver = bool(
            viewer and viewer.is_authenticated and (
                viewer.pk == instance.pk or viewer.user_type == 'admin' or viewer.is_staff
            )
        )
        if not pode_ver:
            for campo in CAMPOS_SENSIVEIS:
                data.pop(campo, None)
        return data


class UserRegisterSerializer(UserSerializer):
    """
    Cadastro público. Exige CPF e endereço e nunca aceita `user_type` do cliente:
    quem se cadastra é sempre cidadão (administradores são criados pelo Django admin).
    """

    class Meta(UserSerializer.Meta):
        read_only_fields = ['is_active', 'user_type']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
            'email':    {'required': True, 'allow_blank': False},
            'cidade':   {'required': True, 'allow_blank': False},
            'bairro':   {'required': True, 'allow_blank': False},
            'numero':   {'required': True, 'allow_blank': False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in ('cpf', 'cep', 'uf'):
            self.fields[nome].required = True
            self.fields[nome].allow_blank = False
            self.fields[nome].allow_null = False

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Já existe um usuário com este e-mail.')
        return value


class UserMeSerializer(UserSerializer):
    """Edição do próprio perfil (`/users/me/`): `user_type` e `setor` são somente leitura."""

    class Meta(UserSerializer.Meta):
        read_only_fields = ['is_active', 'user_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].read_only = True


class UserStaffCreateSerializer(UserSerializer):
    """
    Cadastro de gestor público / equipe técnica feito pelo administrador.
    Exige perfil, setor, cidade e UF (é o que define o que a pessoa enxerga).
    """

    class Meta(UserSerializer.Meta):
        read_only_fields = ['is_active']
        extra_kwargs = {
            'password':  {'write_only': True, 'min_length': 8, 'required': True},
            'email':     {'required': True, 'allow_blank': False},
            'user_type': {'required': True},
            'cidade':    {'required': True, 'allow_blank': False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uf'].required = True
        self.fields['uf'].allow_blank = False
        self.fields['setor'].required = True
        self.fields['setor'].allow_null = False

    def validate_user_type(self, value):
        if value not in PERFIS_MUNICIPAIS:
            raise serializers.ValidationError('Use "gestor" ou "equipe_tecnica".')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Já existe um usuário com este e-mail.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

