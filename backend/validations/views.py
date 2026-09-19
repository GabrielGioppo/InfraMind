from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from validations.models import Validation
from validations.serializers import ValidationSerializer
from occurrences.models import Occurrence
from logs.utils import register_log
from gemini_api.client import analyze_occurrence_urgency, detect_duplicate_occurrences


class ValidationCreateListView(generics.ListCreateAPIView):
    serializer_class = ValidationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Validation.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_occurrence(request, occurrence_id):
    user = request.user

    try:
        occurrence = Occurrence.objects.get(id=occurrence_id)
    except Occurrence.DoesNotExist:
        return Response({'error': 'Ocorrência não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    if occurrence.user == user:
        return Response(
            {'error': 'Você não pode validar a sua própria ocorrência.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if Validation.objects.filter(occurrence=occurrence, user=user).exists():
        return Response(
            {'error': 'Você já validou esta ocorrência.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    validation = Validation.objects.create(user=user, occurrence=occurrence)

    occurrence.validation_count += 1
    from occurrences.views import calculate_priority
    occurrence.priority = calculate_priority(occurrence)
    occurrence.save(update_fields=['validation_count', 'priority'])

    register_log(request, 'validate', 'Occurrence', occurrence.id, {'validated_by': user.username})

    serializer = ValidationSerializer(validation)
    return Response(
        {'message': 'Ocorrência validada com sucesso.', 'validation': serializer.data},
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_analyze_occurrence(request):
    title       = request.data.get('title', '').strip()
    description = request.data.get('description', '').strip()
    latitude    = request.data.get('latitude')
    longitude   = request.data.get('longitude')
    category_id = request.data.get('category_id')
    address     = request.data.get('address', '').strip()

    if not title:
        return Response({'error': 'O campo "title" é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

    urgency = analyze_occurrence_urgency(title, description)

    duplicate_result = {
        'is_duplicate': False,
        'duplicate_of_id': None,
        'similarity_score': 0,
        'reason': 'Nenhuma duplicata encontrada.',
    }

    nearby_qs = Occurrence.objects.filter(status__in=['open', 'in_progress'])
    location_filtered = False

    # Filtro por coordenadas GPS (prioridade)
    if latitude and longitude:
        try:
            lat   = float(latitude)
            lng   = float(longitude)
            delta = 0.5 / 111.0
            nearby_qs = nearby_qs.filter(
                latitude__range=(lat - delta, lat + delta),
                longitude__range=(lng - delta, lng + delta),
            )
            location_filtered = True
        except (ValueError, TypeError):
            pass

    # Fallback: filtro por palavras-chave do endereço textual
    if not location_filtered and address:
        from django.db.models import Q
        keywords = [w for w in address.split() if len(w) > 3]
        if keywords:
            q = Q()
            for kw in keywords[:3]:
                q |= Q(address__icontains=kw)
            nearby_qs = nearby_qs.filter(q)
            location_filtered = True

    # Filtro por categoria
    if category_id:
        nearby_qs = nearby_qs.filter(category_id=category_id)

    existing = list(
        nearby_qs.exclude(title=title).values('id', 'title', 'description', 'address')[:10]
    )

    if existing:
        duplicate_result = detect_duplicate_occurrences(title, description, existing)

    return Response({
        'urgency':              urgency,
        'duplicate':            duplicate_result,
        'similar_occurrences':  existing[:5],
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_ai_prioritized_occurrences(request):
    status_filter   = request.query_params.get('status', 'open')
    category_filter = request.query_params.get('category')
    limit           = int(request.query_params.get('limit', 20))

    qs = Occurrence.objects.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category_id=category_filter)

    occurrences = list(qs.select_related('user', 'category').order_by('-created_at')[:50])

    analyzed = []
    for occ in occurrences:
        urgency = analyze_occurrence_urgency(occ.title, occ.description or '')
        analyzed.append({
            'id':               occ.id,
            'title':            occ.title,
            'description':      occ.description,
            'status':           occ.status,
            'address':          occ.address,
            'category':         occ.category.name if occ.category else None,
            'user':             occ.user.username,
            'validation_count': occ.validation_count,
            'priority':         occ.priority,
            'importance_color': occ.importance_color,
            'is_duplicate':     occ.is_duplicate,
            'duplicate_of':     occ.duplicate_of_id,
            'created_at':       occ.created_at.isoformat(),
            'ai_urgency':       urgency,
        })

    analyzed.sort(
        key=lambda x: (x['ai_urgency']['urgency_score'], x['priority']),
        reverse=True,
    )

    return Response({
        'count':   len(analyzed),
        'results': analyzed[:limit],
    }, status=status.HTTP_200_OK)