from unittest.mock import patch

from django.test import SimpleTestCase

from geo.adapter import OpenStreetMapAdapter


class CidadeEUfTests(SimpleTestCase):
    def test_extrai_cidade_e_uf_do_nominatim(self):
        resposta = {
            'display_name': 'Rua A, Sorocaba, São Paulo, Brasil',
            'address': {'town': 'Sorocaba', 'state': 'São Paulo', 'ISO3166-2-lvl4': 'BR-SP'},
        }
        with patch.object(OpenStreetMapAdapter, '_request', return_value=resposta):
            r = OpenStreetMapAdapter().obter_endereco(-23.5, -47.4)
        self.assertEqual((r['cidade'], r['uf']), ('Sorocaba', 'SP'))
        self.assertEqual(r['endereco_formatado'], 'Rua A, Sorocaba, São Paulo, Brasil')

    def test_falha_devolve_campos_vazios(self):
        with patch.object(OpenStreetMapAdapter, '_request', side_effect=TimeoutError()):
            r = OpenStreetMapAdapter().obter_endereco(-23.5, -47.4)
        self.assertEqual((r['endereco_formatado'], r['cidade'], r['uf']), (None, None, None))
