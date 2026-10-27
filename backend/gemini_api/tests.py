import os
from unittest.mock import patch

from django.test import SimpleTestCase

from gemini_api import client as gemini_client


class GeminiTimeoutTests(SimpleTestCase):
    """RNF02: o cliente do SDK nasce com timeout (5 s por padrão)."""

    def _novo_cliente(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'chave-falsa'}), \
             patch.object(gemini_client.GeminiClient, '_instance', None), \
             patch('google.genai.Client') as sdk:
            gemini_client.GeminiClient()
        return sdk

    def test_timeout_padrao_de_5_segundos(self):
        self.assertEqual(gemini_client.GEMINI_TIMEOUT_SECONDS, 5)
        http_options = self._novo_cliente().call_args.kwargs['http_options']
        self.assertEqual(http_options.timeout, 5000)  # o SDK usa milissegundos

    def test_timeout_vem_da_constante(self):
        with patch.object(gemini_client, 'GEMINI_TIMEOUT_SECONDS', 2.5):
            http_options = self._novo_cliente().call_args.kwargs['http_options']
        self.assertEqual(http_options.timeout, 2500)
