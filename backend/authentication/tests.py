from django.test import TestCase
from rest_framework.test import APIClient

from logs.models import Log
from users.models import User

LOGIN_URL = '/authentication/login/'


class LoginLogTests(TestCase):
    """RF27 / RNF14: todo login bem-sucedido fica registrado no log."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='maria', email='maria@exemplo.com', password='senha-forte-123',
        )
        self.client = APIClient()

    def test_login_valido_grava_log(self):
        resp = self.client.post(
            LOGIN_URL,
            {'email': 'maria@exemplo.com', 'password': 'senha-forte-123'},
            format='json',
            HTTP_USER_AGENT='Firefox/Teste',
            REMOTE_ADDR='203.0.113.7',
        )
        self.assertEqual(resp.status_code, 200)

        log = Log.objects.get(action='login')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.model_name, 'User')
        self.assertEqual(log.object_id, self.user.id)
        self.assertEqual(log.ip_address, '203.0.113.7')
        self.assertEqual(log.device, 'Firefox/Teste')
        self.assertNotIn('password', log.details)

    def test_senha_errada_nao_grava_log(self):
        resp = self.client.post(
            LOGIN_URL, {'email': 'maria@exemplo.com', 'password': 'errada'}, format='json',
        )
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(Log.objects.filter(action='login').exists())
