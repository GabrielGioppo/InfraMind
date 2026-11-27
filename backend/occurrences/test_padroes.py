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


class AvisosAoCidadaoTests(PerfisBase):
    """Toda mudança feita por admin, gestor ou equipe chega no sino de quem registrou a ocorrência."""

    def setUp(self):
        super().setUp()
        self.poste_soro.user = self.cidadao
        self.poste_soro.equipe_responsavel = self.equipe
        self.poste_soro.save()
        self.url = f'/api/v1/occurrences/{self.poste_soro.pk}/'

    def avisos(self):
        return Notificacao.objects.filter(user=self.cidadao, titulo__startswith='Atualização na sua ocorrência')

    def test_gestor_muda_prazo_e_importancia(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.patch(self.url, {'importance_color': 'yellow', 'prazo_definido': '2099-01-01T10:00:00Z'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        msg = self.avisos().get().mensagem
        self.assertIn('importância', msg)
        self.assertIn('prazo', msg)

    def test_equipe_muda_status_avisa_cidadao(self):
        self.client.force_authenticate(self.equipe)
        self.client.patch(self.url, {'status': 'in_progress'}, format='json')
        self.assertIn('Em Andamento', self.avisos().get().mensagem)

    def test_admin_muda_status_avisa_cidadao(self):
        self.client.force_authenticate(self.admin)
        self.client.patch(self.url, {'status': 'in_progress'}, format='json')
        self.assertEqual(self.avisos().count(), 1)

    def test_cidadao_nao_e_avisado_da_propria_mudanca(self):
        self.client.force_authenticate(self.cidadao)
        self.client.patch(self.url, {'title': 'Novo título'}, format='json')
        self.assertFalse(self.avisos().exists())

    def test_sem_mudanca_nao_avisa(self):
        self.client.force_authenticate(self.gestor)
        self.client.patch(self.url, {'importance_color': self.poste_soro.importance_color}, format='json')
        self.assertFalse(self.avisos().exists())

    def test_designacao_e_triagem_avisam_cidadao(self):
        self.poste_soro.equipe_responsavel = None
        self.poste_soro.save()
        self.client.force_authenticate(self.gestor)
        self.client.post(f'{self.url}designar/', {'equipe': self.equipe.pk}, format='json')
        self.assertTrue(Notificacao.objects.filter(user=self.cidadao, titulo__startswith='Equipe designada').exists())
        self.esgoto_soro.user = self.cidadao
        self.esgoto_soro.triagem = 'nova'
        self.esgoto_soro.save()
        self.client.force_authenticate(self.admin)
        self.client.post(f'/api/v1/occurrences/{self.esgoto_soro.pk}/triagem/',
                         {'acao': 'rejeitar', 'observacao': 'Fora da área'}, format='json')
        self.assertTrue(Notificacao.objects.filter(user=self.cidadao, titulo__startswith='Sua ocorrência não foi aceita').exists())

    def test_atualizacao_oficial_avisa_cidadao_e_comentario_avisa_responsaveis(self):
        from feedbacks.models import Feedback
        from occurrences.events import eventos, FEEDBACK_REGISTRADO
        f = Feedback.objects.create(user=self.gestor, occurrence=self.poste_soro, comment='Previsão: dia 02')
        eventos.publicar(FEEDBACK_REGISTRADO, self.poste_soro, por=self.gestor, feedback=f)
        self.assertTrue(Notificacao.objects.filter(user=self.cidadao, titulo__startswith='Atualização oficial').exists())
        c = Feedback.objects.create(user=self.cidadao, occurrence=self.poste_soro, comment='Obrigado', rating=5)
        eventos.publicar(FEEDBACK_REGISTRADO, self.poste_soro, por=self.cidadao, feedback=c)
        self.assertTrue(Notificacao.objects.filter(user=self.gestor, titulo__startswith='Novo comentário').exists())

    def test_rotina_push_nao_duplica_aviso_de_status(self):
        from notifications.services import processar_prazos_e_notificar
        self.client.force_authenticate(self.equipe)
        self.client.patch(self.url, {'status': 'in_progress'}, format='json')
        antes = Notificacao.objects.filter(user=self.cidadao).count()
        processar_prazos_e_notificar('push')
        self.assertEqual(Notificacao.objects.filter(user=self.cidadao).count(), antes)

    def test_admin_recebe_nova_ocorrencia(self):
        from notifications.services import notificar_nova_ocorrencia
        notificar_nova_ocorrencia(self.poste_soro)
        self.assertTrue(Notificacao.objects.filter(user=self.admin, tipo='nova_ocorrencia').exists())

    def test_reenviar_o_mesmo_prazo_nao_vira_mudanca(self):
        from datetime import timedelta
        self.poste_soro.prazo_definido = timezone.now().replace(second=42, microsecond=7) + timedelta(days=3)
        self.poste_soro.save()
        self.client.force_authenticate(self.gestor)
        mesmo_minuto = timezone.localtime(self.poste_soro.prazo_definido).replace(second=0, microsecond=0)
        self.client.patch(self.url, {'prazo_definido': mesmo_minuto.isoformat()}, format='json')
        self.assertFalse(self.avisos().exists())
