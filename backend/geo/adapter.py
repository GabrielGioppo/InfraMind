"""
Adapter (Padrão Estrutural) — geo/adapter.py

Padroniza a obtenção de coordenadas/endereços vindos de fontes externas
diferentes (hoje: OpenStreetMap/Nominatim) atrás de uma interface única
(TargetGeoInterface), pra que o resto do sistema não precise conhecer o
formato de resposta específico de cada provedor de mapas. Se o provedor
for trocado no futuro (ex: Google Maps), basta criar um novo adapter
implementando a mesma interface — nenhuma outra parte do sistema muda.
"""

import json
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod


class TargetGeoInterface(ABC):
    """Interface que qualquer adapter de geolocalização deve implementar."""

    @abstractmethod
    def obter_coordenadas(self, endereco: str) -> dict:
        """Geocodificação direta: endereço → coordenadas."""
        raise NotImplementedError

    @abstractmethod
    def obter_endereco(self, latitude: float, longitude: float) -> dict:
        """Geocodificação reversa: coordenadas → endereço."""
        raise NotImplementedError


class OpenStreetMapAdapter(TargetGeoInterface):
    """
    Adapta a API do OpenStreetMap (Nominatim) pro formato padrão usado
    pelo InfraMind: {'latitude', 'longitude', 'endereco_formatado'}.
    """

    BASE_URL   = 'https://nominatim.openstreetmap.org'
    USER_AGENT = 'InfraMind/1.0 (projeto academico FHO)'

    def _request(self, path: str, params: dict) -> dict | list:
        query = urllib.parse.urlencode(params)
        url = f'{self.BASE_URL}{path}?{query}'
        req = urllib.request.Request(url, headers={
            'User-Agent': self.USER_AGENT,
            'Accept-Language': 'pt-BR',
        })
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode('utf-8'))

    def obter_coordenadas(self, endereco: str) -> dict:
        vazio = {'latitude': None, 'longitude': None, 'endereco_formatado': None}
        if not endereco or not endereco.strip():
            return vazio
        try:
            data = self._request('/search', {'q': endereco, 'format': 'json', 'limit': 1})
            if not data:
                return vazio
            item = data[0]
            return {
                'latitude':            float(item['lat']),
                'longitude':           float(item['lon']),
                'endereco_formatado':  item.get('display_name'),
            }
        except Exception as e:
            print(f'[OpenStreetMapAdapter] Erro na geocodificação direta: {e}')
            return vazio

    def obter_endereco(self, latitude: float, longitude: float) -> dict:
        try:
            data = self._request('/reverse', {'lat': latitude, 'lon': longitude, 'format': 'json'})
            return {
                'latitude':           latitude,
                'longitude':          longitude,
                'endereco_formatado': data.get('display_name'),
            }
        except Exception as e:
            print(f'[OpenStreetMapAdapter] Erro na geocodificação reversa: {e}')
            return {'latitude': latitude, 'longitude': longitude, 'endereco_formatado': None}
