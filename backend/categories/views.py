from rest_framework import generics
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS
from categories.models import Category
from categories.serializers import CategorySerializer


class LeituraPublicaEscritaAdmin(BasePermission):
    """Qualquer pessoa lista/consulta as categorias; só administrador cria, edita ou apaga."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        u = request.user
        return bool(u and u.is_authenticated and (u.user_type == 'admin' or u.is_staff))


class CategoryCreateListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [LeituraPublicaEscritaAdmin]


class CategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [LeituraPublicaEscritaAdmin]
