from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from notifications.models import Notificacao
from notifications.serializers import NotificacaoSerializer
from notifications.services import processar_prazos_e_notificar


class NotificacaoListView(generics.ListAPIView):
    """Lista as notificações do usuário autenticado, mais recentes primeiro."""

    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def processar_prazos_view(request):
    """
    UC-14 — dispara manualmente a verificação de prazos estourados.

    Mesma lógica usada pelo management command `processar_prazos`
    (pensado pra rodar agendado via cron/Celery beat); este endpoint
    existe pra permitir o disparo manual/sob demanda por um admin.
    Body opcional: {"canal": "email" | "push"} (default: "email").
    """
    canal = request.data.get('canal', 'email')
    resultado = processar_prazos_e_notificar(canal=canal)
    return Response(resultado, status=status.HTTP_200_OK)
