import math
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Case, When, IntegerField
from django.utils import timezone

from occurrences.models import Occurrence
from occurrences.serializers import OccurrenceSerializer, OccurrenceAdminSerializer
from history.models import OccurrenceHistory
from logs.utils import register_log
from gemini_api.client import detect_duplicate_occurrences

DUPLICATE_RADIUS_METERS = 50


def get_serializer_class(user):
    if user.user_type == 'admin' or user.is_staff:
        return OccurrenceAdminSerializer
    return OccurrenceSerializer


def calculate_priority(occurrence):
    score = occurrence.validation_count * 2
    days_open = (timezone.now() - occurrence.created_at).days
    score += min(days_open, 10)
    color_score = {'red': 10, 'yellow': 5, 'green': 0}
    score += color_score.get(occurrence.importance_color or 'green', 0)
    return score


def _haversine_meters(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos geográficos."""
    R = 6_371_000
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_duplicate(latitude, longitude, category_id, title, description, address=None):
    """
    Busca duplicatas por coordenadas (raio 50m) ou, como fallback,
    por endereço + categoria quando lat/lng não estão disponíveis.
    """
    has_coords = latitude and longitude

    if has_coords:
        candidates_qs = Occurrence.objects.filter(
            category_id=category_id,
            status__in=['open', 'in_progress'],
            latitude__isnull=False,
            longitude__isnull=False,
        )

        nearby = []
        for occ in candidates_qs:
            dist = _haversine_meters(latitude, longitude, occ.latitude, occ.longitude)
            if dist <= DUPLICATE_RADIUS_METERS:
                nearby.append({
                    'id': occ.pk,
                    'title': occ.title,
                    'description': occ.description or '',
                    'distance_meters': round(dist, 1),
                })

        if not nearby:
            return None

        result = detect_duplicate_occurrences(
            new_title=title,
            new_description=description or '',
            existing_occurrences=nearby,
        )

        if not result.get('is_duplicate'):
            return None

        original_id = result.get('duplicate_of_id')
        if not original_id:
            return None

        try:
            return Occurrence.objects.get(pk=original_id)
        except Occurrence.DoesNotExist:
            return None

    # Fallback: sem coordenadas → compara endereço + categoria
    if not address or not str(address).strip():
        return None

    normalized = address.strip().lower()

    candidates_qs = Occurrence.objects.filter(
        category_id=category_id,
        status__in=['open', 'in_progress'],
    )

    for occ in candidates_qs:
        occ_address = (occ.address or '').strip().lower()
        if not occ_address:
            continue
        if occ_address == normalized or normalized in occ_address or occ_address in normalized:
            return occ

    return None

class OccurrenceCreateListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return get_serializer_class(self.request.user)

    def get_queryset(self):
        user     = self.request.user
        is_admin = user.user_type == 'admin' or user.is_staff

        qs = Occurrence.objects.all()

        status_filter   = self.request.query_params.get('status')
        category_filter = self.request.query_params.get('category')
        date_from       = self.request.query_params.get('date_from')
        date_to         = self.request.query_params.get('date_to')
        urgency_filter  = self.request.query_params.get('urgency')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category_id=category_filter)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if urgency_filter:
            qs = qs.filter(urgency_level=urgency_filter)

        if is_admin:
            qs = qs.annotate(
                urgency_order=Case(
                    When(urgency_level='critica', then=0),
                    When(urgency_level='alta',    then=1),
                    When(urgency_level='media',   then=2),
                    When(urgency_level='baixa',   then=3),
                    default=4,
                    output_field=IntegerField(),
                )
            ).order_by('urgency_order', '-urgency_score', '-priority')

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Verificação de duplicata ANTES de salvar ──────────────────────
        latitude    = request.data.get('latitude')
        longitude   = request.data.get('longitude')
        category_id = request.data.get('category')
        title       = request.data.get('title', '')
        description = request.data.get('description', '')
        address     = request.data.get('address', '')

        original = _find_duplicate(latitude, longitude, category_id, title, description, address)

        if original:
            # Incrementa validação comunitária na ocorrência original
            Occurrence.objects.filter(pk=original.pk).update(
                validation_count=original.validation_count + 1
            )
            original.refresh_from_db()
            new_priority = calculate_priority(original)
            Occurrence.objects.filter(pk=original.pk).update(priority=new_priority)

            original_serializer = get_serializer_class(request.user)(
                original, context={'request': request}
            )
            return Response(
                {
                    'message': 'Ocorrência duplicada detectada. Sua confirmação foi adicionada à ocorrência já existente.',
                    'duplicate': True,
                    'original_occurrence': original_serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        # ─────────────────────────────────────────────────────────────────

        occ = serializer.save(user=request.user)
        register_log(request, 'create', 'Occurrence', occ.id, {'title': occ.title})
        return Response(
            {'message': 'Ocorrência registrada com sucesso.', 'occurrence': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class OccurrenceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return get_serializer_class(self.request.user)

    def get_queryset(self):
        return Occurrence.objects.all()

    def perform_update(self, serializer):
        occurrence      = self.get_object()
        previous_status = occurrence.status
        updated         = serializer.save()

        updated.priority = calculate_priority(updated)
        updated.save(update_fields=['priority'])

        if previous_status != updated.status:
            OccurrenceHistory.objects.create(
                occurrence=updated,
                user=self.request.user,
                previous_status=previous_status,
                new_status=updated.status,
                change_type='status',
            )
            register_log(
                self.request, 'status_change', 'Occurrence', updated.id,
                {'previous': previous_status, 'new': updated.status}
            )
        else:
            register_log(self.request, 'update', 'Occurrence', updated.id, {'title': updated.title})

    def perform_destroy(self, instance):
        register_log(self.request, 'delete', 'Occurrence', instance.id, {'title': instance.title})
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_occurrences(request, lat, lng, radius_km=1):
    try:
        lat    = float(lat)
        lng    = float(lng)
        radius = float(radius_km)
    except ValueError:
        return Response({'error': 'Coordenadas inválidas.'}, status=status.HTTP_400_BAD_REQUEST)

    delta       = radius / 111.0
    occurrences = Occurrence.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        latitude__range=(lat - delta, lat + delta),
        longitude__range=(lng - delta, lng + delta),
    )

    serializer = OccurrenceSerializer(occurrences, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocode_address(request):
    address = request.data.get('address', '').strip()
    if not address:
        return Response(
            {'error': 'O campo "address" é obrigatório.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    return Response({
        'message': 'Use a API de geocodificação do Google Maps no frontend para converter o endereço.',
        'address': address,
    })


# ──────────────────────────────────────────────────────────────
# OCORRÊNCIAS ANÔNIMAS
# ──────────────────────────────────────────────────────────────
from rest_framework.permissions import AllowAny
from occurrences.serializers import AnonOccurrenceSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def create_anonymous_occurrence(request):
    """
    Cria uma ocorrência sem autenticação.
    Requer: anon_id (string gerada pelo browser).
    """
    anon_id = request.data.get('anon_id', '').strip()
    if not anon_id:
        return Response({'error': 'anon_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

    # ── Verificação de duplicata para ocorrências anônimas ────────────
    latitude    = request.data.get('latitude')
    longitude   = request.data.get('longitude')
    category_id = request.data.get('category')
    title       = request.data.get('title', '')
    description = request.data.get('description', '')
    address     = request.data.get('address', '')

    original = _find_duplicate(latitude, longitude, category_id, title, description, address)
    
    if original:
        Occurrence.objects.filter(pk=original.pk).update(
            validation_count=original.validation_count + 1
        )
        return Response(
            {
                'message': 'Ocorrência duplicada detectada. Sua confirmação foi adicionada à ocorrência já existente.',
                'duplicate': True,
                'original_id': original.pk,
                'original_title': original.title,
            },
            status=status.HTTP_200_OK,
        )
    # ─────────────────────────────────────────────────────────────────

    data = {k: v for k, v in request.data.items()}
    data['status'] = 'open'

    serializer = AnonOccurrenceSerializer(data=data)
    if serializer.is_valid():
        occ = serializer.save(user=None, anon_id=anon_id)
        return Response(
            {'id': occ.id, 'anon_id': occ.anon_id, 'title': occ.title},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_anonymous_occurrences(request):
    """
    Vincula ao usuário autenticado todas as ocorrências criadas com o anon_id informado.
    Body: { "anon_id": "anon-..." }
    """
    anon_id = request.data.get('anon_id', '').strip()
    if not anon_id:\
        return Response({'error': 'anon_id é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

    updated = Occurrence.objects.filter(anon_id=anon_id, user__isnull=True).update(
        user=request.user,
        anon_id=None,
    )

    return Response({'claimed': updated}, status=status.HTTP_200_OK)