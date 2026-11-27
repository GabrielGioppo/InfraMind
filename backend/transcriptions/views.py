import logging
from threading import Lock

from rest_framework.decorators import (
    api_view, authentication_classes, parser_classes, permission_classes, throttle_classes,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .serializers import AudioUploadSerializer
from .utils import InvalidAudio, transcribe

logger = logging.getLogger(__name__)
_transcription_slot = Lock()


class AudioThrottle(AnonRateThrottle):
    scope = 'audio_transcription'
    rate = '10/hour'


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser])
@throttle_classes([AudioThrottle])
def transcribe_audio(request):
    # A landing também aceita ocorrências sem login. O áudio é usado apenas
    # para preencher a descrição e não é gravado como anexo da ocorrência.
    serializer = AudioUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'detail': str(serializer.errors['audio'][0])}, status=400)
    audio = serializer.validated_data['audio']
    if not _transcription_slot.acquire(blocking=False):
        return Response({'detail': 'Já há um áudio em processamento. Tente de novo em instantes.'}, status=503, headers={'Retry-After': '5'})
    try:
        transcript = transcribe(audio.file)
    except InvalidAudio as exc:
        return Response({'detail': str(exc)}, status=422)
    except Exception:
        logger.exception('Não foi possível executar a transcrição local')
        return Response({'detail': 'A transcrição está indisponível. Tente novamente ou digite a descrição.'}, status=503)
    finally:
        _transcription_slot.release()
    if not transcript:
        return Response({'detail': 'Nenhuma fala foi identificada no áudio.'}, status=422)
    return Response({'transcript': transcript})
