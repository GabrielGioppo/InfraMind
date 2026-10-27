from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from users.models import User
from users.validators import chave_cidade, cpf_valido

REGISTER_URL = '/api/v1/users/register/'

CPF_OK = '529.982.247-25'   # CPF válido (gerado para teste)


def dados_cadastro(**extra):
    dados = {
        'username': 'maria', 'email': 'maria@exemplo.com', 'password': 'senha-forte-123',
        'cpf': CPF_OK, 'cep': '18030-000', 'logradouro': 'Rua A', 'numero': '120',
        'complemento': 'Ap 3', 'bairro': 'Centro', 'cidade': 'Sorocaba', 'uf': 'sp',
    }
    dados.update(extra)
    return dados


class ValidadoresTests(SimpleTestCase):
    def test_cpf(self):
        self.assertTrue(cpf_valido('52998224725'))
        self.assertTrue(cpf_valido('529.982.247-25'))
        self.assertFalse(cpf_valido('52998224724'))     # dígito errado
        self.assertFalse(cpf_valido('11111111111'))     # repetido
        self.assertFalse(cpf_valido('123'))

    def test_chave_cidade_ignora_acento_caixa_e_espacos(self):
        self.assertEqual(chave_cidade(' São  Paulo '), chave_cidade('sao paulo'))
        self.assertEqual(chave_cidade(None), '')


class CadastroTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_cadastro_completo_normaliza_dados(self):
        resp = self.client.post(REGISTER_URL, dados_cadastro(), format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        u = User.objects.get(username='maria')
        self.assertEqual(u.cpf, '52998224725')
        self.assertEqual(u.cep, '18030000')
        self.assertEqual(u.uf, 'SP')
        self.assertEqual(u.cidade, 'Sorocaba')
        self.assertTrue(u.check_password('senha-forte-123'))

    def test_campos_obrigatorios(self):
        for campo in ('cpf', 'cep', 'cidade', 'uf', 'bairro', 'numero', 'email'):
            dados = dados_cadastro()
            dados.pop(campo)
            resp = self.client.post(REGISTER_URL, dados, format='json')
            self.assertEqual(resp.status_code, 400, campo)
            self.assertIn(campo, resp.json())

    def test_complemento_e_logradouro_sao_opcionais(self):
        dados = dados_cadastro()
        dados.pop('complemento'); dados.pop('logradouro')
        self.assertEqual(self.client.post(REGISTER_URL, dados, format='json').status_code, 201)

    def test_cpf_invalido_e_duplicado(self):
        r = self.client.post(REGISTER_URL, dados_cadastro(cpf='111.111.111-11'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('cpf', r.json())

        self.assertEqual(self.client.post(REGISTER_URL, dados_cadastro(), format='json').status_code, 201)
        r = self.client.post(
            REGISTER_URL, dados_cadastro(username='outra', email='outra@exemplo.com', cpf='52998224725'),
            format='json',
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn('cpf', r.json())

    def test_cep_uf_e_email_invalidos(self):
        self.assertIn('cep', self.client.post(REGISTER_URL, dados_cadastro(cep='123'), format='json').json())
        self.assertIn('uf', self.client.post(REGISTER_URL, dados_cadastro(uf='XX'), format='json').json())
        self.client.post(REGISTER_URL, dados_cadastro(), format='json')
        r = self.client.post(
            REGISTER_URL, dados_cadastro(username='outra', cpf='39053344705', email='MARIA@exemplo.com'),
            format='json',
        )
        self.assertIn('email', r.json())

    def test_cadastro_publico_nunca_cria_admin(self):
        r = self.client.post(REGISTER_URL, dados_cadastro(user_type='admin', is_staff=True), format='json')
        self.assertEqual(r.status_code, 201)
        u = User.objects.get(username='maria')
        self.assertEqual(u.user_type, 'citizen')
        self.assertFalse(u.is_staff)


class PrivacidadeTests(TestCase):
    """CPF e endereço só aparecem para o próprio usuário e para administradores."""

    def setUp(self):
        self.maria = User.objects.create_user(
            username='maria', email='m@x.com', password='x-123456', cpf='52998224725',
            cidade='Sorocaba', uf='SP',
        )
        self.joao = User.objects.create_user(username='joao', email='j@x.com', password='x-123456')
        self.admin = User.objects.create_user(
            username='adm', email='a@x.com', password='x-123456', user_type='admin',
        )

    def _ver(self, quem, alvo):
        c = APIClient()
        c.force_authenticate(quem)
        return c.get(f'/api/v1/users/{alvo.pk}/').json()

    def test_outro_cidadao_nao_ve(self):
        dados = self._ver(self.joao, self.maria)
        self.assertNotIn('cpf', dados)
        self.assertNotIn('cidade', dados)

    def test_proprio_usuario_e_admin_veem(self):
        self.assertEqual(self._ver(self.maria, self.maria)['cpf'], '52998224725')
        self.assertEqual(self._ver(self.admin, self.maria)['cidade'], 'Sorocaba')
