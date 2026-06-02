from rest_framework import serializers
from validations.models import Validation

class ValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validation
        fields = '__all__'