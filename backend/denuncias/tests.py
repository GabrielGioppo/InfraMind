from django.test import TestCase
from rest_framework.test import APIClient

from denuncias.models import Denuncia
from logs.models import Log
from notifications.models import Notificacao
from occurrences.models import Occurrence
from users.models import User

URL = '/api/v1/denuncias/'


def _user(nome, cidade='Sorocaba', **extra):
    return User.objects.create_user(
        username=nome, email=f'{nome}@x.com', password='x-123456', cidade=cidade, uf='SP', **extra,
    )


def _api(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user)
    return c


class DenunciaTests(TestCase):
    def setUp(self):
        self.maria = _user('maria')
        self.joao = _user('joao')
        self.admin = _user('adm', user_type='admin')
        self.occ = Occurrence.objects.create(title='Buraco', user=self.joao, city='Sorocaba', state='SP')
        self.occ_outra_cidade = Occurrence.objects.create(title='Poste', city='Campinas', state='SP')

    def test_relato_de_bug(self):
        r = _api(self.maria).post(URL, {'tipo': 'bug', 'descricao': 'O mapa não carrega no celular.'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        d = Denuncia.objects.get()
        self.assertEqual((d.user, d.tipo, d.status, d.occurrence), (self.maria, 'bug', 'aberta', None))
        self.assertTrue(Log.objects.filter(action='create', model_name='Denuncia', object_id=d.id).exists())

    def test_conteudo_inadequado_exige_ocorrencia(self):
        sem = _api(self.maria).post(URL, {'tipo': 'conteudo_inadequado', 'descricao': 'Foto ofensiva aqui.'}, format='json')
        self.assertEqual(sem.status_code, 400)
        self.assertIn('occurrence', sem.json())
        com = _api(self.maria).post(
            URL, {'tipo': 'conteudo_inadequado', 'descricao': 'Foto ofensiva aqui.', 'occurrence': self.occ.pk},
            format='json',
        )
        self.assertEqual(com.status_code, 201, com.content)

    def test_nao_denuncia_ocorrencia_de_outra_cidade(self):
        r = _api(self.maria).post(
            URL, {'tipo': 'conteudo_inadequado', 'descricao': 'Foto ofensiva aqui.', 'occurrence': self.occ_outra_cidade.pk},
            format='json',
        )
        self.assertEqual(r.status_code, 400)

    def test_descricao_curta_tipo_invalido_e_sem_login(self):
        self.assertEqual(_api(self.maria).post(URL, {'tipo': 'bug', 'descricao': 'curta'}, format='json').status_code, 400)
        self.assertEqual(_api(self.maria).post(URL, {'tipo': 'outro', 'descricao': 'descrição longa o bastante'}, format='json').status_code, 400)
        self.assertEqual(_api().post(URL, {'tipo': 'bug', 'descricao': 'descrição longa o bastante'}, format='json').status_code, 401)

    def test_status_nao_pode_ser_definido_na_criacao(self):
        _api(self.maria).post(URL, {'tipo': 'bug', 'descricao': 'descrição longa o bastante', 'status': 'resolvida'}, format='json')
        self.assertEqual(Denuncia.objects.get().status, 'aberta')

    def _lista(self, user):
        corpo = _api(user).get(URL).json()
        return corpo['results'] if isinstance(corpo, dict) else corpo

    def test_cidadao_ve_so_as_suas_e_admin_ve_todas(self):
        Denuncia.objects.create(user=self.maria, tipo='bug', descricao='da maria, bem longa')
        Denuncia.objects.create(user=self.joao, tipo='bug', descricao='do joao, bem longa')
        self.assertEqual([d['autor'] for d in self._lista(self.maria)], ['maria'])
        self.assertEqual(len(self._lista(self.admin)), 2)

    def test_admin_altera_o_status_e_cidadao_nao(self):
        d = Denuncia.objects.create(user=self.maria, tipo='bug', descricao='da maria, bem longa')
        self.assertEqual(_api(self.maria).patch(f'{URL}{d.pk}/', {'status': 'resolvida'}, format='json').status_code, 403)
        r = _api(self.admin).patch(f'{URL}{d.pk}/', {'status': 'em_analise'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        d.refresh_from_db()
        self.assertEqual(d.status, 'em_analise')
        self.assertEqual(_api(self.admin).patch(f'{URL}{d.pk}/', {'status': 'xx'}, format='json').status_code, 400)

    def test_nova_denuncia_avisa_os_admins_no_sino(self):
        outro_admin = _user('adm2', user_type='admin')
        _api(self.maria).post(URL, {'tipo': 'conteudo_inadequado', 'occurrence': self.occ.pk,
                                    'descricao': 'Esse conteúdo é ofensivo.'}, format='json')
        d = Denuncia.objects.get()
        avisos = Notificacao.objects.filter(titulo=f'Nova denúncia #{d.id}')
        self.assertEqual({n.user for n in avisos}, {self.admin, outro_admin})
        n = avisos.get(user=self.admin)
        self.assertEqual((n.canal, n.tipo, n.read, n.status), ('push', 'geral', False, 'enviada'))
        self.assertIn('maria', n.mensagem)
        self.assertIn('Buraco', n.mensagem)
        # Quem não é admin não recebe nada.
        self.assertFalse(Notificacao.objects.filter(user__in=[self.maria, self.joao]).exists())
        # E o aviso aparece na lista do sino do admin.
        corpo = _api(self.admin).get('/api/v1/notifications/').json()
        lista = corpo['results'] if isinstance(corpo, dict) else corpo
        self.assertEqual([x['titulo'] for x in lista], [f'Nova denúncia #{d.id}'])

    def test_admin_que_denuncia_nao_se_avisa(self):
        _api(self.admin).post(URL, {'tipo': 'bug', 'descricao': 'Teste de bug pelo admin.'}, format='json')
        self.assertFalse(Notificacao.objects.exists())

    def test_falha_no_aviso_nao_derruba_a_denuncia(self):
        from unittest import mock
        with mock.patch('notifications.services._destinatarios_admin', side_effect=RuntimeError('boom')):
            r = _api(self.maria).post(URL, {'tipo': 'bug', 'descricao': 'O mapa não carrega.'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Denuncia.objects.count(), 1)
