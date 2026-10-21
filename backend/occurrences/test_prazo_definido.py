"""Prazo (data e hora) escolhido pelo admin (Occurrence.prazo_definido)."""
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from history.models import OccurrenceHistory
from notifications.models import Notificacao
from notifications.services import processar_prazos_e_notificar
from occurrences.models import Occurrence
from occurrences.serializers import OccurrenceAdminSerializer
from occurrences.sla import SLA_ESTOURADO, prazo_final, sla_status
from users.models import User


def _dt(ano, mes, dia, hora=0, minuto=0, segundo=0):
    return timezone.make_aware(datetime(ano, mes, dia, hora, minuto, segundo))


class PrazoDefinidoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adm', email='a@x.com', password='x', user_type='admin', is_staff=True,
        )
        self.cidadao = User.objects.create_user(
            username='cid', email='c@x.com', password='x',
        )
        self.occ = Occurrence.objects.create(title='Buraco na rua', user=self.cidadao)
        self.url = f'/api/v1/occurrences/{self.occ.pk}/'

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def _patch(self, user, payload):
        return self._client(user).patch(self.url, payload, format='json')

    # ── regra de prazo ────────────────────────────────────────────────
    def test_prazo_definido_tem_prioridade_sobre_horas_estimadas(self):
        self.occ.estimated_time = 1
        self.occ.prazo_definido = _dt(2026, 11, 2, 18, 0)
        self.assertEqual(prazo_final(self.occ), _dt(2026, 11, 2, 18, 0))

    def test_prazo_vencido_estoura_e_adiar_resolve(self):
        self.occ.prazo_definido = timezone.now() - timedelta(days=1)
        self.assertEqual(sla_status(self.occ), SLA_ESTOURADO)
        self.occ.prazo_definido = timezone.now() + timedelta(days=10)
        self.assertNotEqual(sla_status(self.occ), SLA_ESTOURADO)

    def test_encerrada_continua_sem_indicador(self):
        self.occ.prazo_definido = timezone.now() - timedelta(days=1)
        self.occ.status = 'resolved'
        self.assertIsNone(sla_status(self.occ))

    # ── API ───────────────────────────────────────────────────────────
    def test_admin_define_e_reajusta_prazo_com_historico(self):
        r = self._patch(self.admin, {'prazo_definido': '2026-11-02T18:00'})
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.prazo_definido, _dt(2026, 11, 2, 18, 0))

        r = self._patch(self.admin, {'prazo_definido': '2026-11-11T09:30'})
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.prazo_definido, _dt(2026, 11, 11, 9, 30))

        obs = set(
            OccurrenceHistory.objects.filter(occurrence=self.occ, change_type='edit')
            .values_list('observation', flat=True)
        )
        self.assertEqual(obs, {
            'Prazo alterado: sem prazo → 02/11/2026 18:00',
            'Prazo alterado: 02/11/2026 18:00 → 11/11/2026 09:30',
        })

    def test_so_data_sem_horario_vira_23_59_59(self):
        r = self._patch(self.admin, {'prazo_definido': '2026-11-02'})
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.prazo_definido, _dt(2026, 11, 2, 23, 59, 59))

    def test_admin_pode_limpar_o_prazo(self):
        self._patch(self.admin, {'prazo_definido': '2026-11-02T18:00'})
        r = self._patch(self.admin, {'prazo_definido': None})
        self.assertEqual(r.status_code, 200)
        self.occ.refresh_from_db()
        self.assertIsNone(self.occ.prazo_definido)

    def test_mudar_so_o_status_nao_gera_historico_de_prazo(self):
        self._patch(self.admin, {'prazo_definido': '2026-11-02T18:00'})
        self._patch(self.admin, {'status': 'in_progress'})
        self.assertEqual(
            OccurrenceHistory.objects.filter(occurrence=self.occ, change_type='edit').count(), 1,
        )

    def test_cidadao_nao_altera_o_prazo(self):
        self._patch(self.cidadao, {'prazo_definido': '2026-11-02'})
        self.occ.refresh_from_db()
        self.assertIsNone(self.occ.prazo_definido)

    def test_serializer_admin_expoe_prazo_definido_e_limite_calculado(self):
        self.occ.prazo_definido = _dt(2026, 11, 2, 18, 0)
        self.occ.save()
        data = OccurrenceAdminSerializer(self.occ).data
        self.assertTrue(data['prazo_definido'].startswith('2026-11-02T18:00:00'))
        self.assertIsNotNone(data['sla_deadline'])

    # ── notificações (UC-14) ──────────────────────────────────────────
    def test_rotina_de_prazos_usa_o_prazo_definido(self):
        self.occ.prazo_definido = timezone.now() - timedelta(days=1)
        self.occ.save()
        processar_prazos_e_notificar()
        self.assertTrue(
            Notificacao.objects.filter(occurrence=self.occ, tipo='prazo_estourado').exists()
        )
