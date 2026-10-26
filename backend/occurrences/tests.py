from django.test import TestCase
from unittest.mock import patch, MagicMock
from occurrences.models import Occurrence
from gemini_api.client import analyze_occurrence_description_and_photo, clean_truncate


class AIDescriptionAnalysisTests(TestCase):
    """Testes unitários cobrindo a análise de foto e descrição via IA (Gemini / Fallback)"""

    def test_clean_truncate_within_limit(self):
        text = "Texto curto dentro do limite."
        truncated = clean_truncate(text, 255)
        self.assertEqual(truncated, text)

    def test_clean_truncate_exceeding_limit(self):
        long_text = "Esta é uma descrição extremamente longa " * 10  # 400+ caracteres
        truncated = clean_truncate(long_text, 255)
        self.assertLessEqual(len(truncated), 255)
        self.assertTrue(truncated.endswith('...'))
        # Garante que não corta palavra no meio (termina em '...' após palavra completa)
        without_dots = truncated[:-3]
        self.assertFalse(without_dots.endswith(' '))

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_no_description_generates_from_photo(self, mock_gemini_instance):
        """1. Sem descrição -> Status GERADA"""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "GERADA", "descricao_final": "Buraco grande no asfalto com fissuras ao redor.", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description="", title="Buraco")
        self.assertEqual(res['status'], 'GERADA')
        self.assertEqual(res['descricao_final'], "Buraco grande no asfalto com fissuras ao redor.")

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_correct_long_description_mantida(self, mock_gemini_instance):
        """2. Descrição correta e longa -> Status MANTIDA"""
        original = "Existe um buraco profundo no meio da pista de rolamento que oferece risco aos motoristas e motociclistas que passam no local."
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "MANTIDA", "descricao_final": "Texto alterado pela IA que deve ser ignorado", "sugestao": "Risco adicional aos pedestres"}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Buraco")
        self.assertEqual(res['status'], 'MANTIDA')
        # Garantia no código: MANTIDA nunca altera o texto original
        self.assertEqual(res['descricao_final'], original)
        self.assertEqual(res['sugestao'], "Risco adicional aos pedestres")

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_short_objective_description_mantida(self, mock_gemini_instance):
        """3. Descrição curta e objetiva (< 25 caracteres) -> Status MANTIDA (aceita)"""
        original = "Buraco fundo na via"  # 19 caracteres
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "MANTIDA", "descricao_final": "Ignorar", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Buraco")
        self.assertEqual(res['status'], 'MANTIDA')
        self.assertEqual(res['descricao_final'], original)

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_shallow_description_substituida(self, mock_gemini_instance):
        """4. Descrição rasa e genérica -> Status SUBSTITUIDA"""
        original = "problema na rua"
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "SUBSTITUIDA", "descricao_final": "Acúmulo de lixo e entulho obstruindo a calçada.", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Problema")
        self.assertEqual(res['status'], 'SUBSTITUIDA')
        self.assertEqual(res['descricao_final'], "Acúmulo de lixo e entulho obstruindo a calçada.")

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_partially_wrong_description_corrigida(self, mock_gemini_instance):
        """5. Descrição parcialmente errada -> Status CORRIGIDA"""
        original = "Vazamento de água limpa na Rua A nº 50"
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "CORRIGIDA", "descricao_final": "Vazamento de esgoto a céu aberto na Rua A nº 50", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Vazamento")
        self.assertEqual(res['status'], 'CORRIGIDA')
        self.assertIn("Rua A nº 50", res['descricao_final'])

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_totally_different_description_substituida(self, mock_gemini_instance):
        """6. Descrição totalmente diferente da foto -> Status SUBSTITUIDA"""
        original = "Poste com lâmpada queimada"
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "SUBSTITUIDA", "descricao_final": "Cratera no asfalto com afundamento de pista.", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Iluminação")
        self.assertEqual(res['status'], 'SUBSTITUIDA')

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_insufficient_photo(self, mock_gemini_instance):
        """7. Foto insuficiente/escura -> Status FOTO_INSUFICIENTE"""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "FOTO_INSUFICIENTE", "descricao_final": "A imagem está muito escura. Envie uma foto sob luz do dia.", "sugestao": ""}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description="Buraco", title="Buraco")
        self.assertEqual(res['status'], 'FOTO_INSUFICIENTE')
        self.assertEqual(res['descricao_final'], "A imagem está muito escura. Envie uma foto sob luz do dia.")

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_invalid_ai_response_fallback(self, mock_gemini_instance):
        """8. Resposta malformada ou status inválido da IA -> Fallback para FALHA"""
        original = "Descrição original mantida"
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_response = MagicMock()
        mock_response.text = '{"status": "STATUS_INVENTADO_INVALIDO", "descricao_final": "blabla"}'
        mock_client._client.models.generate_content.return_value = mock_response
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Teste")
        self.assertEqual(res['status'], 'FALHA')
        self.assertEqual(res['descricao_final'], original)

    @patch('gemini_api.client.GeminiClient.get_instance')
    def test_ai_error_or_timeout_fallback(self, mock_gemini_instance):
        """9. Erro ou Timeout da API do Gemini -> Fallback para FALHA sem travar registro"""
        original = "Descrição importante que não pode ser perdida"
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client._client.models.generate_content.side_effect = Exception("Timeout de Conexão com Gemini")
        mock_gemini_instance.return_value = mock_client

        res = analyze_occurrence_description_and_photo(image_file=None, description=original, title="Teste")
        self.assertEqual(res['status'], 'FALHA')
        self.assertEqual(res['descricao_final'], original)
