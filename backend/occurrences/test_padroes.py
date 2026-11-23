from datetime import timedelta

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from notifications.models import Notificacao
from occurrences.events import Eventos, Observer, STATUS_ALTERADO
from occurrences.models import Occurrence
from occurrences.priority import (
    PrioridadePadrao, PrioridadePorPrazo, PrioridadePorUrgenciaIA, calcular_prioridade, estrategia_atual,
)
from users.test_perfis import PerfisBase


class StrategyDePrioridadeTests(APITestCase):
    def occ(self, **campos):
        return Occurrence(title='x', validation_count=3, importance_color='red', created_at=timezone.now(), **campos)

    def test_padrao_mantem_a_formula_original(self):
        o = self.occ()
        self.assertEqual(PrioridadePadrao().calcular(o), 3 * 2 + 0 + 10)
        self.assertEqual(calcular_prioridade(o), 16)

    def test_por_prazo_pesa_prazo_estourado_e_proximo(self):
        base = PrioridadePadrao().calcular(self.occ())
        estourado = self.occ(prazo_definido=timezone.now() - timedelta(hours=1))
        proximo = self.occ(prazo_definido=timezone.now() + timedelta(hours=5))
        folgado = self.occ(prazo_definido=timezone.now() + timedelta(days=30))
        s = PrioridadePorPrazo()
        self.assertEqual(s.calcular(estourado), base + 20)
        self.assertEqual(s.calcular(proximo), base + 10)
        self.assertEqual(s.calcular(folgado), base)

    def test_por_prazo_ignora_ocorrencia_encerrada(self):
        o = self.occ(prazo_definido=timezone.now() - timedelta(days=1), status='resolved')
        self.assertEqual(PrioridadePorPrazo().calcular(o), PrioridadePadrao().calcular(o))

    def test_urgencia_ia_soma_a_nota(self):
        o = self.occ(urgency_score=80)
        self.assertEqual(PrioridadePorUrgenciaIA().calcular(o), PrioridadePadrao().calcular(o) + 8)

    def test_escolha_pela_configuracao(self):
        with override_settings(PRIORITY_STRATEGY='por_prazo'):
            self.assertIsInstance(estrategia_atual(), PrioridadePorPrazo)
        with override_settings(PRIORITY_STRATEGY='nao_existe'):
            self.assertIsInstance(estrategia_atual(), PrioridadePadrao)


class _Gravador(Observer):
    def __init__(self):
        self.recebidos = []

    def atualizar(self, evento):
        self.recebidos.append(evento)


class _Quebrado(Observer):
    def atualizar(self, evento):
        raise RuntimeError('defeito')


class ObserverTests(SimpleTestCase):
    def test_observador_inscrito_recebe_o_evento(self):
        ev, g = Eventos(), _Gravador()
        ev.inscrever('a', g)
        ev.publicar('a', 'occ', por='fulano', x=1)
        self.assertEqual((g.recebidos[0].nome, g.recebidos[0].ocorrencia, g.recebidos[0].por, g.recebidos[0].dados), ('a', 'occ', 'fulano', {'x': 1}))

    def test_so_recebe_o_que_assinou_e_nao_duplica(self):
        ev, g = Eventos(), _Gravador()
        ev.inscrever('a', g); ev.inscrever('a', g)
        ev.publicar('a', 1); ev.publicar('b', 2)
        self.assertEqual(len(g.recebidos), 1)

    def test_cancelar_inscricao(self):
        ev, g = Eventos(), _Gravador()
        ev.inscrever('a', g); ev.cancelar('a', g)
        ev.publicar('a', 1)
        self.assertEqual(g.recebidos, [])

    def test_observador_com_defeito_nao_derruba_os_outros(self):
        ev, g = Eventos(), _Gravador()
        ev.inscrever('a', _Quebrado()); ev.inscrever('a', g)
        ev.publicar('a', 1)
        self.assertEqual(len(g.recebidos), 1)


class StatusAlteradoAvisaResponsaveisTests(PerfisBase):
    def test_equipe_muda_status_e_o_gestor_e_avisado(self):
        self.poste_soro.equipe_responsavel = self.equipe
        self.poste_soro.save()
        self.client.force_authenticate(self.equipe)
        r = self.client.patch(f'/api/v1/occurrences/{self.poste_soro.pk}/', {'status': 'in_progress'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Notificacao.objects.filter(user=self.gestor, tipo='status_change', titulo__startswith='Status alterado').exists())
        # quem mudou não é avisado de si mesmo
        self.assertFalse(Notificacao.objects.filter(user=self.equipe, titulo__startswith='Status alterado').exists())

    def test_status_igual_nao_publica_evento(self):
        self.client.force_authenticate(self.gestor)
        self.client.patch(f'/api/v1/occurrences/{self.poste_soro.pk}/', {'importance_color': 'red'}, format='json')
        self.assertFalse(Notificacao.objects.filter(titulo__startswith='Status alterado').exists())
