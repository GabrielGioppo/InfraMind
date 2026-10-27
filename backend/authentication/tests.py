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

    def test_login_por_usuario_tambem_grava_log(self):
        # É o caminho que o site usa primeiro (SimpleJWT, /authentication/token/).
        resp = self.client.post(
            '/authentication/token/', {'username': 'maria', 'password': 'senha-forte-123'},
            format='json', REMOTE_ADDR='203.0.113.9',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.json())
        log = Log.objects.get(action='login')
        self.assertEqual((log.user, log.ip_address), (self.user, '203.0.113.9'))

    def test_login_por_usuario_com_senha_errada_nao_grava_log(self):
        resp = self.client.post(
            '/authentication/token/', {'username': 'maria', 'password': 'errada'}, format='json',
        )
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(Log.objects.filter(action='login').exists())

    def test_senha_errada_nao_grava_log(self):
        resp = self.client.post(
            LOGIN_URL, {'email': 'maria@exemplo.com', 'password': 'errada'}, format='json',
        )
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(Log.objects.filter(action='login').exists())


# ──────────────────────────────────────────────────────────────
# UC-02 — recuperação de senha
# ──────────────────────────────────────────────────────────────
import re

from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from notifications.models import Notificacao

RESET_URL = '/authentication/password-reset/'
CONFIRM_URL = '/authentication/password-reset/confirm/'


@override_settings(EMAIL_HOST='smtp.teste.local', FRONTEND_URL='http://app.local/index.html')
class RecuperacaoDeSenhaTests(TestCase):
    def setUp(self):
        cache.clear()   # zera o limite de pedidos por IP entre os testes
        self.user = User.objects.create_user(
            username='maria', email='maria@exemplo.com', password='senha-antiga-123',
        )
        self.client = APIClient()

    def _pedir_link(self):
        self.client.post(RESET_URL, {'email': 'maria@exemplo.com'}, format='json')
        corpo = mail.outbox[-1].body
        return re.search(r'reset_uid=([^&\s]+)&reset_token=([^\s]+)', corpo).groups()

    def test_pedido_envia_email_com_link(self):
        resp = self.client.post(RESET_URL, {'email': 'MARIA@exemplo.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['maria@exemplo.com'])
        self.assertIn('http://app.local/index.html?reset_uid=', mail.outbox[0].body)

    def test_email_desconhecido_responde_igual_e_nao_envia(self):
        resp = self.client.post(RESET_URL, {'email': 'ninguem@exemplo.com'}, format='json')
        igual = self.client.post(RESET_URL, {'email': 'maria@exemplo.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), igual.json())
        self.assertEqual(len(mail.outbox), 1)   # só o do e-mail que existe

    def test_pedido_sem_email_e_400(self):
        self.assertEqual(self.client.post(RESET_URL, {}, format='json').status_code, 400)

    def test_link_nao_fica_no_banco_nem_no_sino(self):
        self._pedir_link()
        n = Notificacao.objects.get(tipo='recuperacao_senha')
        self.assertEqual(n.status, 'enviada')
        self.assertNotIn('reset_token', n.mensagem)
        c = APIClient(); c.force_authenticate(self.user)
        corpo = c.get('/api/v1/notifications/').json()
        itens = corpo['results'] if isinstance(corpo, dict) else corpo
        self.assertEqual(itens, [])

    def test_confirmar_troca_a_senha_e_o_link_so_vale_uma_vez(self):
        uid, token = self._pedir_link()
        r = self.client.post(CONFIRM_URL, {'uid': uid, 'token': token, 'password': 'Nova-senha-9876'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Nova-senha-9876'))
        login = self.client.post(
            LOGIN_URL, {'email': 'maria@exemplo.com', 'password': 'Nova-senha-9876'}, format='json',
        )
        self.assertEqual(login.status_code, 200)

        de_novo = self.client.post(CONFIRM_URL, {'uid': uid, 'token': token, 'password': 'Outra-senha-5555'}, format='json')
        self.assertEqual(de_novo.status_code, 400)

    def test_token_e_uid_invalidos(self):
        uid, token = self._pedir_link()
        for dados in (
            {'uid': uid, 'token': 'token-errado', 'password': 'Nova-senha-9876'},
            {'uid': 'xx', 'token': token, 'password': 'Nova-senha-9876'},
            {'uid': '', 'token': '', 'password': 'Nova-senha-9876'},
        ):
            self.assertEqual(self.client.post(CONFIRM_URL, dados, format='json').status_code, 400, dados)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('senha-antiga-123'))

    def test_senha_fraca_e_recusada_e_o_link_continua_valido(self):
        uid, token = self._pedir_link()
        r = self.client.post(CONFIRM_URL, {'uid': uid, 'token': token, 'password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.json())
        ok = self.client.post(CONFIRM_URL, {'uid': uid, 'token': token, 'password': 'Nova-senha-9876'}, format='json')
        self.assertEqual(ok.status_code, 200)

    def test_link_expira(self):
        uid, token = self._pedir_link()
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            r = self.client.post(CONFIRM_URL, {'uid': uid, 'token': token, 'password': 'Nova-senha-9876'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_limite_de_pedidos_por_ip(self):
        codigos = [self.client.post(RESET_URL, {'email': 'x@y.com'}, format='json').status_code for _ in range(11)]
        self.assertEqual(codigos[:10], [200] * 10)
        self.assertEqual(codigos[10], 429)
