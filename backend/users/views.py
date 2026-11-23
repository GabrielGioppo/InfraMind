from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated, SAFE_METHODS
from django.contrib.auth import get_user_model
from users.perfis import is_admin
from users.serializers import (
    UserMeSerializer, UserRegisterSerializer, UserSerializer, UserStaffCreateSerializer,
)

User = get_user_model()

class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    # Cadastro público: exige CPF/endereço e nunca aceita user_type (sempre cidadão).
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(
                {'message': 'Usuário criado com sucesso.', 'user': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SoAdministrador(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_admin(request.user))


class ProprioOuAdministrador(BasePermission):
    """Qualquer usuário logado consulta; só o próprio usuário ou um administrador altera/apaga."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.pk == request.user.pk or is_admin(request.user)


class UserStaffCreateView(generics.CreateAPIView):
    """POST /api/v1/users/staff/ — o administrador cadastra gestor público ou equipe técnica."""
    queryset = User.objects.all()
    serializer_class = UserStaffCreateSerializer
    permission_classes = [SoAdministrador]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response({'message': 'Usuário criado com sucesso.', 'user': serializer.data},
                        status=status.HTTP_201_CREATED)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [ProprioOuAdministrador]

class UserMeView(generics.RetrieveUpdateAPIView):
    # O próprio usuário edita o perfil, mas não pode mudar o próprio user_type.
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
