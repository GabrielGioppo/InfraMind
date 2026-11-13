"""
Padrão Observer — eventos do ciclo de vida da ocorrência.

As views só *publicam* o que aconteceu (`eventos.publicar(...)`); quem quiser reagir (avisar
gestores, equipe, etc.) se *inscreve* como observador. Assim a view não conhece nenhum
destinatário, e novas reações entram sem alterá-la. Veja `occurrences/observers.py`.
"""
from dataclasses import dataclass, field

OCORRENCIA_CRIADA = 'ocorrencia_criada'
OCORRENCIA_TRIADA = 'ocorrencia_triada'
OCORRENCIA_DESIGNADA = 'ocorrencia_designada'
STATUS_ALTERADO = 'status_alterado'


@dataclass
class Evento:
    nome: str
    ocorrencia: object
    por: object = None                      # quem causou o evento (pode ser None: anônimo)
    dados: dict = field(default_factory=dict)


class Observer:
    """Interface: recebe cada evento em que está inscrito."""

    def atualizar(self, evento: Evento) -> None:
        raise NotImplementedError


class Eventos:
    """O 'Subject': guarda os observadores por evento e os avisa em ordem de inscrição."""

    def __init__(self):
        self._observadores: dict[str, list[Observer]] = {}

    def inscrever(self, nome: str, observador: Observer) -> None:
        lista = self._observadores.setdefault(nome, [])
        if observador not in lista:
            lista.append(observador)

    def cancelar(self, nome: str, observador: Observer) -> None:
        if observador in self._observadores.get(nome, []):
            self._observadores[nome].remove(observador)

    def publicar(self, nome: str, ocorrencia, por=None, **dados) -> None:
        evento = Evento(nome, ocorrencia, por, dados)
        for observador in list(self._observadores.get(nome, [])):
            try:
                observador.atualizar(evento)
            except Exception as e:  # um observador com defeito não derruba a ação principal nem os outros
                print(f'[eventos] {type(observador).__name__} falhou em {nome}: {e}')


eventos = Eventos()
