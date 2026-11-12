import math
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Case, When, IntegerField
from rest_framework.views import APIView
from django.utils import timezone

from occurrences.models import Occurrence
from occurrences.serializers import (
    OccurrenceSerializer, OccurrenceAdminSerializer, OccurrenceEquipeSerializer, TriagemSerializer,
)
from history.models import OccurrenceHistory
from logs.utils import register_log
from gemini_api.facade import IAProcessamentoFacade
from occurrences.visibility import visible_occurrences
from users.perfis import is_admin as _is_admin, is_equipe, is_gestor, is_municipal
from users.models import User
from users.validators import chave_cidade

from gemini_api.client import analyze_occurrence_description_and_photo
from images.models import Image

DUPLICATE_RADIUS_METERS = 50


def get_serializer_class(user, method='GET'):
    # Administrador e gestor público editam os dados de gestão (importância, prazo, status...).
    if _is_admin(user) or user.user_type == 'gestor':
        return OccurrenceAdminSerializer
    # Equipe técnica: ao registrar uma ocorrência age como cidadão; no resto só atualiza o status.
    if is_equipe(user):
        return OccurrenceSerializer if method == 'POST' else OccurrenceEquipeSerializer
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

        result = IAProcessamentoFacade().processar_novo_chamado(
            title=title,
            description=description or '',
            nearby_occurrences=nearby,
        )['duplicidade']

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
        return get_serializer_class(self.request.user, self.request.method)

    def get_queryset(self):
        user     = self.request.user
        is_admin = _is_admin(user) or is_municipal(user)

        qs = visible_occurrences(user)

        status_filter   = self.request.query_params.get('status')
        category_filter = self.request.query_params.get('category')
        date_from       = self.request.query_params.get('date_from')
        date_to         = self.request.query_params.get('date_to')
        urgency_filter  = self.request.query_params.get('urgency')
        triagem_filter  = self.request.query_params.get('triagem')

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
        if triagem_filter:
            qs = qs.filter(triagem=triagem_filter)

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

        # Extrai foto do request se enviada junto
        image_file = request.FILES.get('image') or request.FILES.get('image_file')
        if not image_file and 'image' in request.FILES:
            files = request.FILES.getlist('image')
            if files:
                image_file = files[0]

        latitude    = request.data.get('latitude')
        longitude   = request.data.get('longitude')
        category_id = request.data.get('category')
        title       = request.data.get('title', '')
        description = request.data.get('description', '')
        address     = request.data.get('address', '')

        # ── Análise da Foto e Descrição pela IA (ANTES de salvar) ─────────
        ai_analysis = analyze_occurrence_description_and_photo(
            image_file=image_file,
            description=description,
            title=title
        )

        # ── Verificação de duplicata ANTES de salvar ──────────────────────
        original = _find_duplicate(latitude, longitude, category_id, title, ai_analysis['descricao_final'], address)

        if original:
            Occurrence.objects.filter(pk=original.pk).update(
                validation_count=original.validation_count + 1
            )
            original.refresh_from_db()
            new_priority = calculate_priority(original)
            Occurrence.objects.filter(pk=original.pk).update(priority=new_priority)

            original_serializer = get_serializer_class(request.user, 'POST')(
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

        # Cidade/UF vêm da geocodificação feita pelo app; se não vierem, vale a cidade
        # do cadastro do usuário.
        city  = (serializer.validated_data.get('city') or request.user.cidade or '').strip()
        state = (serializer.validated_data.get('state') or request.user.uf or '').strip()

        occ = serializer.save(
            user=request.user,
            city=city,
            state=state,
            description=ai_analysis['descricao_final'],
            original_description=ai_analysis['original_description'],
            description_analysis_status=ai_analysis['status'],
            description_suggestion=ai_analysis['sugestao']
        )

        # Se foto foi enviada no payload de criação, salva no modelo Image
        if image_file:
            try:
                Image.objects.create(occurrence=occ, user=request.user, image=image_file)
            except Exception as e:
                print(f"Erro ao salvar imagem principal: {e}")

        register_log(request, 'create', 'Occurrence', occ.id, {'title': occ.title})
        _avisar_gestores_nova(occ)
        res_data = self.get_serializer(occ, context={'request': request}).data
        return Response(
            {
                'message': 'Ocorrência registrada com sucesso.',
                'occurrence': res_data,
                'description_analysis': ai_analysis
            },
            status=status.HTTP_201_CREATED,
        )


class OccurrenceRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return get_serializer_class(self.request.user, self.request.method)

    def get_queryset(self):
        return visible_occurrences(self.request.user)

    def perform_update(self, serializer):
        occurrence      = self.get_object()
        user            = self.request.user
        previous_status = occurrence.status
        previous_deadline = occurrence.prazo_definido

        # Equipe técnica só atualiza o que foi designado a ela.
        if is_equipe(user) and occurrence.equipe_responsavel_id != user.id:
            raise PermissionDenied('Esta ocorrência não foi designada para você.')

        # Encerramento com evidência: Resolvida exige parecer e foto da resolução.
        novo_status = serializer.validated_data.get('status')
        if novo_status == 'resolved' and previous_status != 'resolved':
            parecer = serializer.validated_data.get('parecer_encerramento', occurrence.parecer_encerramento)
            erros = {}
            if not (parecer or '').strip():
                erros['parecer_encerramento'] = 'Escreva o parecer do atendimento.'
            if not occurrence.images.filter(etapa='resolucao').exists():
                erros['evidencia'] = 'Anexe ao menos uma foto da resolução.'
            if erros:
                raise ValidationError({'status': 'Para marcar como Resolvida é preciso o parecer e a foto da resolução.', **erros})

        updated         = serializer.save()

        update_fields = ['priority']
        updated.priority = calculate_priority(updated)
        if updated.status == 'resolved' and not updated.resolved_at:
            updated.resolved_at = timezone.now()
            update_fields.append('resolved_at')
        updated.save(update_fields=update_fields)

        if previous_deadline != updated.prazo_definido:
            fmt_prazo = lambda d: timezone.localtime(d).strftime('%d/%m/%Y %H:%M') if d else 'sem prazo'
            antes  = fmt_prazo(previous_deadline)
            depois = fmt_prazo(updated.prazo_definido)
            OccurrenceHistory.objects.create(
                occurrence=updated,
                user=self.request.user,
                previous_status=updated.status,
                new_status=updated.status,
                change_type='edit',
                observation=f'Prazo alterado: {antes} → {depois}',
            )

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
        if is_municipal(self.request.user):
            raise PermissionDenied('Gestor público e equipe técnica não excluem ocorrências.')
        register_log(self.request, 'delete', 'Occurrence', instance.id, {'title': instance.title})
        instance.delete()


class OccurrenceTriagemView(APIView):
    """
    POST /api/v1/occurrences/<id>/triagem/ — o gestor (ou o administrador) tria uma ocorrência nova.

    aprovar:  define importância e prazo e, se for o caso, encaminha para o setor certo.
    rejeitar: encerra a ocorrência com o motivo (ex.: conteúdo falso ou fora do escopo).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (_is_admin(user) or is_gestor(user)):
            raise PermissionDenied('Só o administrador e o gestor público fazem a triagem.')
        try:
            occ = visible_occurrences(user).get(pk=pk)
        except Occurrence.DoesNotExist:
            return Response({'detail': 'Ocorrência não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if occ.triagem != 'nova':
            return Response({'detail': 'Esta ocorrência já passou pela triagem.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TriagemSerializer(data=request.data, context={'occurrence': occ, 'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        dados = serializer.validated_data

        with transaction.atomic():
            if dados['acao'] == 'rejeitar':
                self._rejeitar(request, occ, dados['observacao'].strip())
            else:
                self._aprovar(request, occ, dados)

        occ.refresh_from_db()
        # Se o gestor encaminhou para outro setor, a ocorrência sai da área dele: devolve o resumo mesmo assim.
        saida = get_serializer_class(user)(occ, context={'request': request}).data
        return Response(saida, status=status.HTTP_200_OK)

    @staticmethod
    def _marcar(occ, user, resultado, obs=''):
        occ.triagem, occ.triagem_em, occ.triagem_por, occ.triagem_obs = resultado, timezone.now(), user, obs

    def _aprovar(self, request, occ, dados):
        antes_setor = occ.category
        if 'importance_color' in dados:
            occ.importance_color = dados['importance_color']
        if 'prazo_definido' in dados:
            occ.prazo_definido = dados['prazo_definido']
        if 'category' in dados:
            if dados['category'] != occ.category:
                occ.subcategory = None            # a subcategoria antiga era do setor anterior
            occ.category = dados['category']
        if 'subcategory' in dados:
            occ.subcategory = dados['subcategory']
        self._marcar(occ, request.user, 'triada')
        if is_gestor(request.user) and not occ.gestor_responsavel_id and occ.category_id == request.user.setor_id:
            occ.gestor_responsavel = request.user
        occ.priority = calculate_priority(occ)
        occ.save()

        rotulos = dict(Occurrence.IMPORTANCE_CHOICES)
        prazo = timezone.localtime(occ.prazo_definido).strftime('%d/%m/%Y %H:%M')
        texto = f'Triagem aprovada: importância {rotulos.get(occ.importance_color)}; prazo {prazo}'
        if occ.category_id != (antes_setor.pk if antes_setor else None):
            de = antes_setor.name if antes_setor else 'sem setor'
            texto += f'; encaminhada de {de} para {occ.category.name}'
        if (dados.get('observacao') or '').strip():
            texto += f'. Obs.: {dados["observacao"].strip()}'
        OccurrenceHistory.objects.create(
            occurrence=occ, user=request.user, previous_status=occ.status, new_status=occ.status,
            change_type='edit', observation=texto,
        )
        register_log(request, 'update', 'Occurrence', occ.id, {'triagem': 'aprovada', 'detalhe': texto})
        # Avisa os gestores do setor responsável quando a triagem veio de fora dele (admin ou outro setor).
        if _is_admin(request.user) or occ.category_id != (antes_setor.pk if antes_setor else None):
            from notifications.services import notificar_encaminhamento
            notificar_encaminhamento(occ, request.user)

    def _rejeitar(self, request, occ, motivo):
        anterior = occ.status
        self._marcar(occ, request.user, 'rejeitada', motivo)
        occ.status = 'closed'
        occ.save()
        OccurrenceHistory.objects.create(
            occurrence=occ, user=request.user, previous_status=anterior, new_status='closed',
            change_type='status', observation=f'Triagem rejeitada: {motivo}',
        )
        register_log(request, 'status_change', 'Occurrence', occ.id,
                     {'triagem': 'rejeitada', 'previous': anterior, 'new': 'closed', 'motivo': motivo})


def _avisar_gestores_nova(occ):
    """Nunca derruba o cadastro da ocorrência se o aviso falhar."""
    try:
        from notifications.services import notificar_nova_ocorrencia
        notificar_nova_ocorrencia(occ)
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao avisar gestores: {e}")


def _da_area(pessoa, occ) -> bool:
    """A pessoa é do setor e da cidade da ocorrência?"""
    return (
        bool(occ.category_id) and pessoa.setor_id == occ.category_id
        and bool(occ.city_key) and chave_cidade(pessoa.cidade) == occ.city_key
        and (pessoa.uf or '').strip().upper() == occ.state
    )


class OccurrenceDesignarView(APIView):
    """
    POST /api/v1/occurrences/<id>/designar/ — define quem responde pela ocorrência já triada.

    {"equipe": <id|null>}  equipe técnica do setor/cidade (precisa estar disponível). Admin e gestor.
    {"gestor": <id|null>}  gestor público do setor/cidade. Só o administrador.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        if not (_is_admin(user) or is_gestor(user)):
            raise PermissionDenied('Só o administrador e o gestor público designam a ocorrência.')
        try:
            occ = visible_occurrences(user).get(pk=pk)
        except Occurrence.DoesNotExist:
            return Response({'detail': 'Ocorrência não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if occ.triagem != 'triada':
            return Response({'detail': 'Faça a triagem antes de designar.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ('equipe' in request.data or 'gestor' in request.data):
            return Response({'detail': 'Informe "equipe" e/ou "gestor".'}, status=status.HTTP_400_BAD_REQUEST)

        mudancas, avisar = [], None
        if 'equipe' in request.data:
            nova, erro = self._escolher(request.data.get('equipe'), 'equipe_tecnica', occ, occ.equipe_responsavel_id)
            if erro:
                return Response({'equipe': erro}, status=status.HTTP_400_BAD_REQUEST)
            if nova != occ.equipe_responsavel:
                occ.equipe_responsavel = nova
                mudancas.append(f'equipe técnica: {nova.username if nova else "ninguém"}')
                avisar = nova
        if 'gestor' in request.data:
            if not _is_admin(user):
                raise PermissionDenied('Só o administrador designa o gestor.')
            novo, erro = self._escolher(request.data.get('gestor'), 'gestor', occ, occ.gestor_responsavel_id)
            if erro:
                return Response({'gestor': erro}, status=status.HTTP_400_BAD_REQUEST)
            if novo != occ.gestor_responsavel:
                occ.gestor_responsavel = novo
                mudancas.append(f'gestor: {novo.username if novo else "ninguém"}')

        if mudancas:
            with transaction.atomic():
                occ.save()
                texto = 'Designação — ' + '; '.join(mudancas)
                OccurrenceHistory.objects.create(
                    occurrence=occ, user=user, previous_status=occ.status, new_status=occ.status,
                    change_type='edit', observation=texto)
                register_log(request, 'update', 'Occurrence', occ.id, {'designacao': texto})
            if avisar:
                from notifications.services import notificar_designacao
                notificar_designacao(occ, avisar, user)
        occ.refresh_from_db()
        return Response(get_serializer_class(user)(occ, context={'request': request}).data)

    @staticmethod
    def _escolher(valor, perfil, occ, atual_id):
        """Devolve (usuário|None, erro). valor vazio = remover a designação."""
        if valor in (None, '', 0, '0'):
            return None, None
        pessoa = User.objects.filter(pk=valor, user_type=perfil, is_active=True).first()
        if not pessoa:
            return None, 'Pessoa não encontrada com esse perfil.'
        if not _da_area(pessoa, occ):
            return None, 'Essa pessoa não é do setor e da cidade desta ocorrência.'
        if perfil == 'equipe_tecnica' and not pessoa.disponivel and pessoa.pk != atual_id:
            return None, 'Essa pessoa está marcada como indisponível.'
        return pessoa, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def designacao_candidatos(request, pk):
    """GET /api/v1/occurrences/<id>/candidatos/ — quem pode ser designado (setor + cidade da ocorrência)."""
    user = request.user
    if not (_is_admin(user) or is_gestor(user)):
        raise PermissionDenied('Só o administrador e o gestor público designam a ocorrência.')
    try:
        occ = visible_occurrences(user).get(pk=pk)
    except Occurrence.DoesNotExist:
        return Response({'detail': 'Ocorrência não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    def lista(perfil):
        pessoas = User.objects.filter(user_type=perfil, is_active=True, setor_id=occ.category_id) if occ.category_id else []
        return [{'id': p.id, 'username': p.username, 'nome': (p.get_full_name() or p.username), 'disponivel': p.disponivel}
                for p in pessoas if _da_area(p, occ)]

    return Response({
        'equipe': lista('equipe_tecnica'),
        'gestores': lista('gestor') if _is_admin(user) else [],
        'equipe_atual': occ.equipe_responsavel_id,
        'gestor_atual': occ.gestor_responsavel_id,
    })


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
    occurrences = visible_occurrences(request.user).filter(
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

    image_file = request.FILES.get('image') or request.FILES.get('image_file')
    if not image_file and 'image' in request.FILES:
        files = request.FILES.getlist('image')
        if files:
            image_file = files[0]

    latitude    = request.data.get('latitude')
    longitude   = request.data.get('longitude')
    category_id = request.data.get('category')
    title       = request.data.get('title', '')
    description = request.data.get('description', '')
    address     = request.data.get('address', '')

    # Análise de Foto e Descrição pela IA
    ai_analysis = analyze_occurrence_description_and_photo(
        image_file=image_file,
        description=description,
        title=title
    )

    original = _find_duplicate(latitude, longitude, category_id, title, ai_analysis['descricao_final'], address)
    
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

    data = {k: v for k, v in request.data.items()}
    data['status'] = 'open'
    data['description'] = ai_analysis['descricao_final']
    data['original_description'] = ai_analysis['original_description']
    data['description_analysis_status'] = ai_analysis['status']
    data['description_suggestion'] = ai_analysis['sugestao']

    serializer = AnonOccurrenceSerializer(data=data)
    if serializer.is_valid():
        occ = serializer.save(
            user=None,
            anon_id=anon_id,
            description=ai_analysis['descricao_final'],
            original_description=ai_analysis['original_description'],
            description_analysis_status=ai_analysis['status'],
            description_suggestion=ai_analysis['sugestao']
        )
        if image_file:
            try:
                Image.objects.create(occurrence=occ, user=None, image=image_file)
            except Exception as e:
                print(f"Erro ao salvar imagem anônima: {e}")

        _avisar_gestores_nova(occ)
        res_data = AnonOccurrenceSerializer(occ).data
        return Response(
            {
                'id': occ.id,
                'anon_id': occ.anon_id,
                'title': occ.title,
                'occurrence': res_data,
                'description_analysis': ai_analysis
            },
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

    pendentes = Occurrence.objects.filter(anon_id=anon_id, user__isnull=True)
    # Ocorrência anônima sem cidade herda a cidade de quem a reivindica.
    for occ in pendentes.filter(city=''):
        occ.city, occ.state = request.user.cidade, request.user.uf
        occ.save(update_fields=['city', 'state'])
    updated = pendentes.update(
        user=request.user,
        anon_id=None,
    )

    return Response({'claimed': updated}, status=status.HTTP_200_OK)