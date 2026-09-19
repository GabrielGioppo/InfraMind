from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from feedbacks.models import Feedback
from feedbacks.serializers import FeedbackSerializer, AdminFeedbackSerializer


def get_feedback_serializer(user):
    """Retorna o serializer correto baseado no tipo de usuário"""
    if user.user_type == 'admin' or user.is_staff:
        return AdminFeedbackSerializer
    return FeedbackSerializer


class FeedbackCreateListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return get_feedback_serializer(self.request.user)

    def get_queryset(self):
        user = self.request.user
        is_admin = user.user_type == 'admin' or user.is_staff

        # Admins veem todos os feedbacks
        if is_admin:
            return Feedback.objects.all().order_by('-created_at')

        # Usuários comuns veem todos os feedbacks (visibilidade pública)
        # mas só podem editar/excluir os seus próprios (controlado em outra view)
        occurrence_id = self.request.query_params.get('occurrence')
        if occurrence_id:
            return Feedback.objects.filter(occurrence_id=occurrence_id).order_by('-created_at')

        # Retorna feedbacks da ocorrência do usuário ou todos se nenhum filtro
        return Feedback.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            user = request.user
            is_admin = user.user_type == 'admin' or user.is_staff
            msg = 'Atualização registrada com sucesso.' if is_admin else 'Feedback registrado com sucesso.'
            return Response(
                {'message': msg, 'feedback': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedbackRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return get_feedback_serializer(self.request.user)

    def get_queryset(self):
        user = self.request.user
        is_admin = user.user_type == 'admin' or user.is_staff
        if is_admin:
            return Feedback.objects.all()
        # Usuários comuns só podem editar/excluir os seus próprios feedbacks
        return Feedback.objects.filter(user=user)
