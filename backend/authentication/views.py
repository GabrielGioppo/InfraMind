from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from authentication.throttles import PasswordResetThrottle
from logs.utils import register_log
from notifications.factory import EmailNotifFactory

User = get_user_model()


class LoggedTokenObtainPairView(TokenObtainPairView):
    """
    Login por usuário e senha (/authentication/token/). É o mesmo da SimpleJWT,
    mas grava o login no log (RF27 / RNF14), como o login por e-mail.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        user = serializer.user
        register_log(request, 'login', 'User', user.id, {'email': user.email}, user=user)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_by_email(request):
    email    = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({'error': 'E-mail e senha são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({'error': 'Credenciais inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({'error': 'Usuário inativo.'}, status=status.HTTP_401_UNAUTHORIZED)

    # RF27 / RNF14: registra o login (usuário, IP e dispositivo).
    register_log(request, 'login', 'User', user.id, {'email': user.email}, user=user)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_200_OK)



# ──────────────────────────────────────────────────────────────
# UC-02 — Recuperação de senha
# ──────────────────────────────────────────────────────────────
MSG_RESET_SOLICITADO = (
    'Se o e-mail estiver cadastrado, enviaremos um link para redefinir a senha.'
)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_request(request):
    """
    POST /authentication/password-reset/  {"email": "..."}

    Envia por e-mail (EmailNotifFactory) um link com o token do Django. A resposta
    é sempre a mesma, exista o e-mail ou não, para não revelar quem tem conta.
    """
    email = (request.data.get('email') or '').strip()
    if not email:
        return Response({'error': 'Informe o e-mail.'}, status=status.HTTP_400_BAD_REQUEST)

    for user in User.objects.filter(email__iexact=email, is_active=True):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link = f'{settings.FRONTEND_URL}?reset_uid={uid}&reset_token={token}'
        mensagem = (
            f'Olá, {user.first_name or user.username}.\n\n'
            'Recebemos um pedido para redefinir a senha da sua conta no InfraMind. '
            'Abra o link abaixo para criar uma nova senha (ele vale por 1 hora):\n\n'
            f'{link}\n\n'
            'Se você não fez esse pedido, ignore este e-mail: sua senha continua a mesma.'
        )
        notificacao = EmailNotifFactory().notificar(
            user, 'InfraMind — redefinição de senha', mensagem, tipo='recuperacao_senha',
        )
        # O link não precisa ficar guardado no banco depois de enviado.
        notificacao.mensagem = 'Link de redefinição de senha enviado por e-mail.'
        notificacao.save(update_fields=['mensagem'])
        register_log(request, 'update', 'User', user.id,
                     {'evento': 'redefinicao_de_senha_solicitada'}, user=user)

    return Response({'message': MSG_RESET_SOLICITADO}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_confirm(request):
    """POST /authentication/password-reset/confirm/  {"uid", "token", "password"}"""
    uid = request.data.get('uid') or ''
    token = request.data.get('token') or ''
    password = request.data.get('password') or ''

    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uid).decode(), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError, UnicodeDecodeError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return Response(
            {'error': 'Link inválido ou expirado. Peça um novo link de redefinição.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({'password': list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)   # troca o hash, o que invalida o link usado
    user.save()
    register_log(request, 'update', 'User', user.id,
                 {'evento': 'senha_redefinida'}, user=user)
    return Response({'message': 'Senha redefinida com sucesso.'}, status=status.HTTP_200_OK)
