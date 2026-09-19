from rest_framework import serializers
from history.models import OccurrenceHistory


class OccurrenceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OccurrenceHistory
        fields = '__all__'
        read_only_fields = ['user', 'changed_at']
