from gemini_api.client import detect_duplicate_occurrences


class AudioTranscriber:
  
    def transcrever(self, audio_file) -> str:
        if not audio_file:
            return ''
        # TODO(UC-04): enviar audio_file pro Gemini e devolver o texto transcrito.
        return ''


class ImageAnalyzer:
 
    def analisar(self, image_file) -> str:
        if not image_file:
            return ''
        # TODO(UC-05): enviar image_file pro Gemini e devolver a descrição gerada.
        return ''


class DuplicidadeChecker:
   
    def verificar(self, title: str, description: str, existing_occurrences: list) -> dict:
        return detect_duplicate_occurrences(title, description, existing_occurrences)


class IAProcessamentoFacade:

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