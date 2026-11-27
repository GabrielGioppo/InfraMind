from functools import lru_cache
from itertools import chain

from django.conf import settings

SAMPLE_RATE = 16000
MAX_SECONDS = 60


class InvalidAudio(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_model():
    from faster_whisper import WhisperModel

    model_name = settings.WHISPER_MODEL
    cache_dir = settings.BASE_DIR / 'venv' / 'whisper-models'
    local_model = cache_dir / model_name
    if all(
        (local_model / filename).is_file()
        for filename in ('model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt')
    ):
        model_name = str(local_model)
    return WhisperModel(
        model_name,
        device='cpu',
        compute_type='int8',
        cpu_threads=2,
        download_root=str(cache_dir),
    )


def _decode_audio(source):
    import av
    import numpy as np

    chunks = []
    samples = 0
    try:
        with av.open(source) as container:
            if not container.streams.audio:
                raise InvalidAudio('O arquivo não contém áudio.')
            resampler = av.AudioResampler(format='s16', layout='mono', rate=SAMPLE_RATE)
            for frame in chain(container.decode(audio=0), (None,)):
                for output in resampler.resample(frame):
                    samples += output.samples
                    if samples > SAMPLE_RATE * MAX_SECONDS:
                        raise InvalidAudio('O áudio deve ter até 60 segundos.')
                    chunks.append(output.to_ndarray().ravel())
    except (av.error.FFmpegError, EOFError, OSError) as exc:
        raise InvalidAudio('Não consegui ler esse áudio. Use WAV, MP3, OGG, M4A ou WebM.') from exc
    if not samples:
        raise InvalidAudio('O arquivo de áudio está vazio.')
    return np.concatenate(chunks).astype(np.float32) / 32768


def transcribe(source):
    audio = _decode_audio(source)
    segments, _ = _load_model().transcribe(
        audio,
        language='pt',
        beam_size=5,
        vad_filter=True,
        temperature=0,
        condition_on_previous_text=False,
        initial_prompt=(
            'Ocorrência urbana. Asfalto, buracos na via, iluminação pública, '
            'calçada, bueiro, alagamento, lixo e semáforo.'
        ),
    )
    return ' '.join(segment.text.strip() for segment in segments).strip()
