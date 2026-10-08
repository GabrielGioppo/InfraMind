from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from logs.models import Log
from logs.serializers import LogSerializer

# Logs só acessíveis por administradores
class LogCreateListView(generics.ListCreateAPIView):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAdminUser]

class LogRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAdminUser]
