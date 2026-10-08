from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import Notificacao
from notifications.serializers import NotificacaoSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/v1/notifications/ — notificações do usuário autenticado."""
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, pk):
    try:
        notif = Notificacao.objects.get(pk=pk, user=request.user)
    except Notificacao.DoesNotExist:
        return Response({'error': 'Notificação não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
    notif.read = True
    notif.save(update_fields=['read'])
    return Response({'read': True})
