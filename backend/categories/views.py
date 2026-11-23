from rest_framework import generics
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS
from categories.models import Category, Subcategory
from categories.serializers import CategorySerializer, SubcategorySerializer


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



class SubcategoryListCreateView(generics.ListCreateAPIView):
    """GET /api/v1/categories/subcategories/?category=<id> — lista; POST (admin) cria."""
    serializer_class = SubcategorySerializer
    permission_classes = [LeituraPublicaEscritaAdmin]

    def get_queryset(self):
        qs = Subcategory.objects.select_related('category')
        u = self.request.user
        if not (u.is_authenticated and (u.user_type == 'admin' or u.is_staff)):
            qs = qs.filter(is_active=True)
        categoria = self.request.query_params.get('category')
        if categoria:
            qs = qs.filter(category_id=categoria)
        return qs


class SubcategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubcategorySerializer
    permission_classes = [LeituraPublicaEscritaAdmin]
    queryset = Subcategory.objects.select_related('category')
