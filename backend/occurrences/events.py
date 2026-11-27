from dataclasses import dataclass, field

OCORRENCIA_CRIADA = 'ocorrencia_criada'
OCORRENCIA_TRIADA = 'ocorrencia_triada'
OCORRENCIA_DESIGNADA = 'ocorrencia_designada'
STATUS_ALTERADO = 'status_alterado'
OCORRENCIA_ATUALIZADA = 'ocorrencia_atualizada'   # dados['mudancas']: lista de textos já legíveis
TRIAGEM_REJEITADA = 'triagem_rejeitada'            # dados['motivo']
FEEDBACK_REGISTRADO = 'feedback_registrado'        # dados['feedback']


@dataclass
class Evento:
    nome: str
    ocorrencia: object
    por: object = None                    
    dados: dict = field(default_factory=dict)


class Observer:

    def atualizar(self, evento: Evento) -> None:
        raise NotImplementedError


class Eventos:

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
            except Exception as e:  
                print(f'[eventos] {type(observador).__name__} falhou em {nome}: {e}')


eventos = Eventos()
