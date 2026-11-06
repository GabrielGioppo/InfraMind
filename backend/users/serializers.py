from rest_framework import serializers
from django.contrib.auth import get_user_model

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

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'date_of_birth', 'phone', 'address',
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
