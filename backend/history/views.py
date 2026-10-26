from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from history.models import OccurrenceHistory
from history.serializers import OccurrenceHistorySerializer
from occurrences.visibility import visible_occurrences

class OccurrenceHistoryListView(generics.ListAPIView):
    serializer_class = OccurrenceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        occurrence_id = self.kwargs.get('occurrence_id')
        visiveis = visible_occurrences(self.request.user)
        return OccurrenceHistory.objects.filter(occurrence_id=occurrence_id, occurrence__in=visiveis)