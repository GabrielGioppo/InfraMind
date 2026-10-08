from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from geo.adapter import OpenStreetMapAdapter


@api_view(['GET'])
@permission_classes([AllowAny])
def reverse_geocode(request):
    """GET /api/v1/geo/reverse/?lat=...&lng=... — coordenadas → endereço."""
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    if not lat or not lng:
        return Response(
            {'error': 'Os parâmetros "lat" e "lng" são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        lat, lng = float(lat), float(lng)
    except ValueError:
        return Response({'error': 'Coordenadas inválidas.'}, status=status.HTTP_400_BAD_REQUEST)

    resultado = OpenStreetMapAdapter().obter_endereco(lat, lng)
    return Response(resultado)


@api_view(['GET'])
@permission_classes([AllowAny])
def forward_geocode(request):
    """GET /api/v1/geo/search/?address=... — endereço → coordenadas."""
    address = request.query_params.get('address', '').strip()
    if not address:
        return Response(
            {'error': 'O parâmetro "address" é obrigatório.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resultado = OpenStreetMapAdapter().obter_coordenadas(address)
    return Response(resultado)
