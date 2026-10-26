from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from denuncias.models import Denuncia
from denuncias.serializers import DenunciaSerializer, DenunciaStatusSerializer
from logs.utils import register_log
from occurrences.visibility import is_admin


class DenunciaListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/denuncias/  — o cidadão vê as suas; o administrador vê todas.
    POST /api/v1/denuncias/  — registra uma denúncia ou um pedido de suporte.
    """
    serializer_class = DenunciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Denuncia.objects.select_related('user', 'occurrence')
        user = self.request.user
        return qs if is_admin(user) else qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        denuncia = serializer.save(user=request.user)
        register_log(request, 'create', 'Denuncia', denuncia.id, {'tipo': denuncia.tipo})
        return Response(
            {'message': 'Recebemos sua mensagem. Obrigado por avisar!', 'denuncia': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class DenunciaStatusView(generics.UpdateAPIView):
    """PATCH /api/v1/denuncias/<id>/  {"status": "em_analise"} — só administrador."""
    queryset = Denuncia.objects.all()
    serializer_class = DenunciaStatusSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch', 'options']

    def check_permissions(self, request):
        super().check_permissions(request)
        if not is_admin(request.user):
            raise PermissionDenied('Apenas administradores podem alterar o status.')

    def perform_update(self, serializer):
        anterior = serializer.instance.status
        denuncia = serializer.save()
        register_log(self.request, 'update', 'Denuncia', denuncia.id,
                     {'status_anterior': anterior, 'status_novo': denuncia.status})
