from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from logs.models import Log
from notifications.factory import EmailNotifFactory
from notifications.models import Notificacao
from notifications.services import processar_prazos_e_notificar
from occurrences.models import Occurrence
from occurrences.serializers import OccurrenceAdminSerializer, OccurrenceSerializer
from occurrences.sla import SLA_ESTOURADO, SLA_OK, SLA_PROXIMO, sla_status
from users.models import User


def _occ(horas_atras, estimated_time=10, status='open', user=None):
    occ = Occurrence.objects.create(
        title='Buraco na rua', user=user, status=status, estimated_time=estimated_time,
    )
    Occurrence.objects.filter(pk=occ.pk).update(
        created_at=timezone.now() - timedelta(hours=horas_atras)
    )
    occ.refresh_from_db()
    return occ


class SlaStatusTests(TestCase):
    def test_ok_proximo_estourado(self):
        self.assertEqual(sla_status(_occ(1)), SLA_OK)
        self.assertEqual(sla_status(_occ(9)), SLA_PROXIMO)
        self.assertEqual(sla_status(_occ(11)), SLA_ESTOURADO)

    def test_sem_prazo_ou_encerrada_nao_tem_indicador(self):
        self.assertIsNone(sla_status(_occ(50, estimated_time=None)))
        self.assertIsNone(sla_status(_occ(50, status='resolved')))

    def test_serializers_expoem_indicador(self):
        occ = _occ(11)
        for cls in (OccurrenceSerializer, OccurrenceAdminSerializer):
            data = cls(occ).data
            self.assertEqual(data['sla_status'], SLA_ESTOURADO)
            self.assertIsNotNone(data['sla_deadline'])


class AuditoriaNotificacaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cidadao', email='c@x.com', password='x',
        )

    def test_envio_registra_log(self):
        n = EmailNotifFactory().notificar(self.user, 't', 'm')
        log = Log.objects.get(action='notification_sent')
        self.assertEqual(log.object_id, n.id)
        self.assertEqual(log.model_name, 'Notificacao')
        self.assertEqual(log.details['canal'], 'email')

    def test_falha_registra_log_com_erro_e_nao_interrompe(self):
        with patch.object(EmailNotifFactory, '_enviar', side_effect=RuntimeError('smtp fora')):
            n = EmailNotifFactory().notificar(self.user, 't', 'm')
        self.assertEqual(n.status, 'falha')
        log = Log.objects.get(action='notification_failed')
        self.assertEqual(log.details['erro'], 'smtp fora')

    def test_rotina_prazos_registra_log_por_notificacao(self):
        _occ(11, user=self.user)
        processar_prazos_e_notificar()
        self.assertEqual(
            Log.objects.filter(action='notification_sent').count(),
            Notificacao.objects.filter(status='enviada').count(),
        )
        self.assertGreater(Log.objects.count(), 0)
