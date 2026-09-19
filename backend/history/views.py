from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from history.models import OccurrenceHistory
from history.serializers import OccurrenceHistorySerializer

class OccurrenceHistoryListView(generics.ListAPIView):
    serializer_class = OccurrenceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        occurrence_id = self.kwargs.get('occurrence_id')
        return OccurrenceHistory.objects.filter(occurrence_id=occurrence_id)