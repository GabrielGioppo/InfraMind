from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from images.models import Image
from images.serializers import ImageSerializer

class ImageCreateListView(generics.ListCreateAPIView):
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(
                {'message': 'Imagem enviada com sucesso.', 'image': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from occurrences.models import Occurrence


@api_view(['POST'])
@permission_classes([AllowAny])
def create_anonymous_image(request):
    """
    Faz upload de imagem para uma ocorrência anônima (sem autenticação).
    Aceita multipart/form-data com: occurrence (id) + image_file.
    Só permite vincular a ocorrências que ainda não têm usuário (anônimas).
    """
    occurrence_id = request.data.get('occurrence')
    image_file = request.FILES.get('image_file') or request.FILES.get('image')

    if not occurrence_id or not image_file:
        return Response(
            {'error': 'occurrence e image_file são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        occ = Occurrence.objects.get(pk=occurrence_id, user__isnull=True)
    except Occurrence.DoesNotExist:
        return Response(
            {'error': 'Ocorrência não encontrada ou já vinculada a um usuário.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    img = Image.objects.create(occurrence=occ, user=None, image=image_file)
    return Response({'id': img.id}, status=status.HTTP_201_CREATED)
