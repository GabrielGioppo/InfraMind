from rest_framework.test import APITestCase

from categories.models import Category
from occurrences.models import Occurrence
from occurrences.visibility import visible_occurrences
from users.models import User

SENHA = 'Senha-12345'


def _user(nome, **extra):
    return User.objects.create_user(username=nome, email=f'{nome}@x.com', password=SENHA, **extra)


class PerfisBase(APITestCase):
    def setUp(self):
        self.iluminacao = Category.objects.get(name='Iluminação pública')
        self.saneamento = Category.objects.get(name='Saneamento básico')
        self.admin = _user('adm', user_type='admin')
        self.gestor = _user('gestor', user_type='gestor', setor=self.iluminacao, cidade='Sorocaba', uf='SP')
        self.equipe = _user('equipe', user_type='equipe_tecnica', setor=self.iluminacao, cidade='sorocaba', uf='sp')
        self.cidadao = _user('cid', cidade='Sorocaba', uf='SP')
        self.outro_gestor = _user('g2', user_type='gestor', setor=self.saneamento, cidade='Sorocaba', uf='SP')
        self.gestor_campinas = _user('g3', user_type='gestor', setor=self.iluminacao, cidade='Campinas', uf='SP')

        def occ(titulo, cat, cidade, autor=None):
            return Occurrence.objects.create(title=titulo, category=cat, city=cidade, state='SP', user=autor or self.cidadao,
                                             triagem='triada')

        self.poste_soro = occ('Poste Sorocaba', self.iluminacao, 'Sorocaba')
        self.esgoto_soro = occ('Esgoto Sorocaba', self.saneamento, 'Sorocaba')
        self.poste_camp = occ('Poste Campinas', self.iluminacao, 'Campinas')
        self.sem_setor = occ('Sem setor', None, 'Sorocaba')

    def titulos(self, user):
        return sorted(o.title for o in visible_occurrences(user))


class VisibilidadeDeGestorEEquipeTests(PerfisBase):
    def test_gestor_ve_so_o_setor_dele_na_cidade_dele(self):
        self.assertEqual(self.titulos(self.gestor), ['Poste Sorocaba'])
        self.assertEqual(self.titulos(self.outro_gestor), ['Esgoto Sorocaba'])
        self.assertEqual(self.titulos(self.gestor_campinas), ['Poste Campinas'])

    def test_equipe_tecnica_segue_a_mesma_regra_sem_acento_nem_caixa(self):
        self.assertEqual(self.titulos(self.equipe), ['Poste Sorocaba'])

    def test_gestor_sem_setor_ou_cidade_ve_so_o_que_registrou(self):
        sem_setor = _user('semsetor', user_type='gestor', cidade='Sorocaba', uf='SP')
        sem_cidade = _user('semcidade', user_type='gestor', setor=self.iluminacao)
        propria = Occurrence.objects.create(title='Minha', user=sem_setor)
        self.assertEqual(self.titulos(sem_setor), ['Minha'])
        self.assertEqual(self.titulos(sem_cidade), [])
        self.assertTrue(propria.pk)

    def test_gestor_ve_a_propria_ocorrencia_mesmo_de_outro_setor(self):
        Occurrence.objects.create(title='Dele', user=self.gestor, category=self.saneamento, city='Sorocaba', state='SP')
        self.assertIn('Dele', self.titulos(self.gestor))

    def test_cidadao_continua_vendo_a_cidade_toda_e_admin_tudo(self):
        self.assertEqual(len(self.titulos(self.cidadao)), 4)
        self.assertEqual(len(self.titulos(self.admin)), 4)

    def test_lista_da_api_respeita_o_perfil(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.get('/api/v1/occurrences/')
        self.assertEqual(r.status_code, 200)
        dados = r.json() if isinstance(r.json(), list) else r.json()['results']
        self.assertEqual([o['title'] for o in dados], ['Poste Sorocaba'])


class PermissoesNasOcorrenciasTests(PerfisBase):
    def _url(self, occ):
        return f'/api/v1/occurrences/{occ.pk}/'

    def test_gestor_define_importancia_e_prazo(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.patch(self._url(self.poste_soro), {'importance_color': 'red', 'status': 'in_progress'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.poste_soro.refresh_from_db()
        self.assertEqual((self.poste_soro.importance_color, self.poste_soro.status), ('red', 'in_progress'))

    def test_equipe_so_altera_o_status(self):
        self.poste_soro.equipe_responsavel = self.equipe
        self.poste_soro.save()
        self.client.force_authenticate(self.equipe)
        r = self.client.patch(self._url(self.poste_soro),
                              {'status': 'in_progress', 'importance_color': 'red', 'title': 'Hackeado'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.poste_soro.refresh_from_db()
        self.assertEqual(self.poste_soro.status, 'in_progress')
        self.assertEqual(self.poste_soro.title, 'Poste Sorocaba')
        self.assertNotEqual(self.poste_soro.importance_color, 'red')

    def test_gestor_nao_mexe_em_ocorrencia_de_outro_setor_ou_cidade(self):
        self.client.force_authenticate(self.gestor)
        for occ in (self.esgoto_soro, self.poste_camp):
            self.assertEqual(self.client.patch(self._url(occ), {'status': 'closed'}, format='json').status_code, 404)

    def test_gestor_e_equipe_nao_excluem(self):
        for u in (self.gestor, self.equipe):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.delete(self._url(self.poste_soro)).status_code, 403)
        self.assertTrue(Occurrence.objects.filter(pk=self.poste_soro.pk).exists())

    def test_admin_exclui(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(self._url(self.poste_soro)).status_code, 204)


class CadastroDeGestorTests(PerfisBase):
    URL = '/api/v1/users/staff/'

    def _corpo(self, **extra):
        return {'username': 'novo', 'email': 'novo@x.com', 'password': 'Senha-12345', 'user_type': 'gestor',
                'setor': self.iluminacao.pk, 'cidade': 'Sorocaba', 'uf': 'SP', **extra}

    def test_so_admin_cadastra(self):
        self.assertEqual(self.client.post(self.URL, self._corpo()).status_code, 401)
        for u in (self.cidadao, self.gestor, self.equipe):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.post(self.URL, self._corpo()).status_code, 403)
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.URL, self._corpo())
        self.assertEqual(r.status_code, 201, r.content)
        novo = User.objects.get(username='novo')
        self.assertEqual((novo.user_type, novo.setor_id, novo.cidade, novo.uf), ('gestor', self.iluminacao.pk, 'Sorocaba', 'SP'))
        self.assertTrue(novo.check_password('Senha-12345'))
        self.assertEqual(r.json()['user']['setor_nome'], 'Iluminação pública')

    def test_exige_setor_cidade_uf_e_perfil_valido(self):
        self.client.force_authenticate(self.admin)
        for faltando in ('setor', 'cidade', 'uf'):
            corpo = self._corpo(); corpo.pop(faltando)
            self.assertEqual(self.client.post(self.URL, corpo).status_code, 400, faltando)
        self.assertEqual(self.client.post(self.URL, self._corpo(user_type='admin')).status_code, 400)
        self.assertEqual(self.client.post(self.URL, self._corpo(user_type='citizen')).status_code, 400)

    def test_recusa_email_repetido_e_senha_fraca(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.URL, self._corpo(email='ADM@x.com')).status_code, 400)
        self.assertEqual(self.client.post(self.URL, self._corpo(password='12345678')).status_code, 400)

    def test_admin_troca_o_setor_e_o_perfil_de_alguem(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f'/api/v1/users/{self.gestor.pk}/', {'setor': self.saneamento.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.gestor.refresh_from_db()
        self.assertEqual(self.gestor.setor_id, self.saneamento.pk)
        # promover um cidadão a gestor sem setor/cidade completos é recusado
        sem = _user('sem')
        r = self.client.patch(f'/api/v1/users/{sem.pk}/', {'user_type': 'gestor'}, format='json')
        self.assertEqual(r.status_code, 400)


class ProtecaoDePerfilTests(PerfisBase):
    def test_usuario_nao_se_promove_nem_muda_o_proprio_setor(self):
        self.client.force_authenticate(self.cidadao)
        for url in (f'/api/v1/users/{self.cidadao.pk}/', '/api/v1/users/me/'):
            self.client.patch(url, {'user_type': 'admin', 'setor': self.iluminacao.pk, 'first_name': 'Zé'}, format='json')
        self.cidadao.refresh_from_db()
        self.assertEqual((self.cidadao.user_type, self.cidadao.setor_id), ('citizen', None))
        self.assertEqual(self.cidadao.first_name, 'Zé')   # o resto da edição continua valendo

    def test_usuario_nao_edita_nem_apaga_outro(self):
        self.client.force_authenticate(self.cidadao)
        url = f'/api/v1/users/{self.gestor.pk}/'
        self.assertEqual(self.client.patch(url, {'first_name': 'X'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.get(url).status_code, 200)   # consultar continua liberado

    def test_gestor_nao_muda_a_propria_cidade(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.patch('/api/v1/users/me/', {'cidade': 'Campinas'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.gestor.refresh_from_db()
        self.assertEqual(self.gestor.cidade, 'Sorocaba')
        r = self.client.patch('/api/v1/users/me/', {'first_name': 'Maria'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)

    def test_admin_edita_qualquer_um(self):
        self.client.force_authenticate(self.admin)
        r = self.client.patch(f'/api/v1/users/{self.cidadao.pk}/', {'first_name': 'Novo'}, format='json')
        self.assertEqual(r.status_code, 200)
