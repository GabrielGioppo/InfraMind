"""
Façade (Padrão Estrutural) — gemini_api/facade.py

Unifica o processamento inteligente de uma nova ocorrência atrás de uma
única interface (IAProcessamentoFacade.processar_novo_chamado), escondendo
do OcorrenciaController (occurrences/views.py) a complexidade de acionar
cada subsistema de IA individualmente: transcrição de áudio, análise de
imagem e checagem de duplicidade.
"""

from gemini_api.client import detect_duplicate_occurrences


class AudioTranscriber:
    """
    UC-04 (Transcrever Áudio de Ocorrência) — ainda não implementado.
    Quando a integração real com o Gemini for feita, este método passa a
    enviar o arquivo de áudio pro modelo (speech-to-text) e devolver o
    texto transcrito.
    """

    def transcrever(self, audio_file) -> str:
        if not audio_file:
            return ''
        # TODO(UC-04): enviar audio_file pro Gemini e devolver o texto transcrito.
        return ''


class ImageAnalyzer:
    """
    UC-05 (Gerar Descrição Automática por Imagem) — ainda não implementado.
    Quando a integração real com o Gemini for feita, este método passa a
    enviar a imagem pro modelo multimodal e devolver a descrição gerada.
    """

    def analisar(self, image_file) -> str:
        if not image_file:
            return ''
        # TODO(UC-05): enviar image_file pro Gemini e devolver a descrição gerada.
        return ''


class DuplicidadeChecker:
    """
    Encapsula a checagem de duplicidade (UC-06, já implementado).
    Recebe a lista de ocorrências candidatas — já filtradas por raio de
    50m e categoria por quem chama, em occurrences/views.py — e decide,
    via Gemini ou fallback local (Jaccard), se a nova ocorrência é
    duplicata de alguma delas.
    """

    def verificar(self, title: str, description: str, existing_occurrences: list) -> dict:
        return detect_duplicate_occurrences(title, description, existing_occurrences)


class IAProcessamentoFacade:
    """
    Façade — ponto único de acesso ao processamento inteligente de um novo
    chamado. As views de Occurrence não precisam conhecer AudioTranscriber,
    ImageAnalyzer ou DuplicidadeChecker individualmente; chamam apenas
    processar_novo_chamado().
    """

    def __init__(self):
        self._audio_transcriber   = AudioTranscriber()
        self._image_analyzer      = ImageAnalyzer()
        self._duplicidade_checker = DuplicidadeChecker()

    def processar_novo_chamado(
        self,
        title: str,
        description: str,
        nearby_occurrences: list = None,
        audio_file=None,
        image_file=None,
    ) -> dict:
        """
        Orquestra o enriquecimento e a triagem de uma nova ocorrência:
        1. Transcreve o áudio (se houver) e anexa ao texto da descrição.
        2. Gera descrição a partir da imagem (se houver) e anexa também.
        3. Checa duplicidade contra as ocorrências próximas já filtradas
           por quem chamou (o raio/categoria é regra de negócio do domínio
           de Ocorrência, não da IA).
        """
        transcricao_audio = self._audio_transcriber.transcrever(audio_file)
        descricao_imagem  = self._image_analyzer.analisar(image_file)

        descricao_final = description or ''
        if transcricao_audio:
            descricao_final = f'{descricao_final}\n{transcricao_audio}'.strip()
        if descricao_imagem:
            descricao_final = f'{descricao_final}\n{descricao_imagem}'.strip()

        duplicidade = self._duplicidade_checker.verificar(
            title, descricao_final, nearby_occurrences or []
        )

        return {
            'description':        descricao_final,
            'transcricao_audio':  transcricao_audio,
            'descricao_imagem':   descricao_imagem,
            'duplicidade':        duplicidade,
        }