from rest_framework import views, response, status
from rest_framework.permissions import AllowAny
from users.models import User
from occurrences.models import Occurrence
from categories.models import Category

class ApiStatsView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        total_usuarios    = User.objects.count()
        total_ocorrencias = Occurrence.objects.count()
        total_categorias  = Category.objects.count()

        return response.Response(data={
            'total_usuarios':    total_usuarios,
            'total_ocorrencias': total_ocorrencias,
            'total_categorias':  total_categorias,
        }, status=status.HTTP_200_OK)