from django.test import TestCase
from rest_framework.test import APIClient

from occurrences.models import Occurrence
from occurrences.visibility import visible_occurrences
from users.models import User

LISTA = '/api/v1/occurrences/'


def _user(nome, cidade='', uf='', **extra):
    return User.objects.create_user(
        username=nome, email=f'{nome}@x.com', password='x-123456', cidade=cidade, uf=uf, **extra,
    )


class VisibilidadePorCidadeTests(TestCase):
    def setUp(self):
        self.maria = _user('maria', 'Sorocaba', 'SP')
        self.joao = _user('joao', 'Sorocaba', 'SP')
        self.ana = _user('ana', 'Campinas', 'SP')
        self.admin = _user('adm', user_type='admin')
        self.sem_cidade = _user('antigo')   # cadastro anterior ao campo de cidade

        self.soro = Occurrence.objects.create(title='Buraco', user=self.joao, city='Sorocaba', state='SP')
        self.camp = Occurrence.objects.create(title='Poste', user=self.ana, city='Campinas', state='SP')
        self.sem = Occurrence.objects.create(title='Antiga', user=self.ana)
        self.mesma_cidade_outra_uf = Occurrence.objects.create(
            title='Homônima', user=self.ana, city='Sorocaba', state='RJ',
        )

    def _titulos(self, user):
        return sorted(o.title for o in visible_occurrences(user))

    def test_cidadao_ve_so_a_propria_cidade(self):
        self.assertEqual(self._titulos(self.maria), ['Buraco'])
        self.assertEqual(self._titulos(self.ana), ['Antiga', 'Homônima', 'Poste'])  # as dela, mesmo fora da cidade

    def test_cidade_e_comparada_sem_acento_nem_caixa(self):
        so = _user('so', 'sao paulo', 'sp')
        Occurrence.objects.create(title='SP', user=self.ana, city='São Paulo', state='SP')
        self.assertEqual(self._titulos(so), ['SP'])

    def test_cidadao_sem_cidade_ve_so_as_proprias(self):
        propria = Occurrence.objects.create(title='Minha', user=self.sem_cidade)
        self.assertEqual(self._titulos(self.sem_cidade), [propria.title])

    def test_admin_ve_tudo(self):
        self.assertEqual(len(self._titulos(self.admin)), 4)

    def test_api_lista_e_detalhe(self):
        c = APIClient(); c.force_authenticate(self.maria)
        corpo = c.get(LISTA).json()
        itens = corpo['results'] if isinstance(corpo, dict) else corpo
        self.assertEqual([o['title'] for o in itens], ['Buraco'])
        self.assertEqual(c.get(f'{LISTA}{self.soro.pk}/').status_code, 200)
        self.assertEqual(c.get(f'{LISTA}{self.camp.pk}/').status_code, 404)

        a = APIClient(); a.force_authenticate(self.admin)
        self.assertEqual(a.get(f'{LISTA}{self.camp.pk}/').status_code, 200)

    def test_proximidade_respeita_a_cidade(self):
        Occurrence.objects.filter(pk=self.soro.pk).update(latitude=-23.5, longitude=-47.4)
        Occurrence.objects.filter(pk=self.camp.pk).update(latitude=-23.5, longitude=-47.4)
        c = APIClient(); c.force_authenticate(self.maria)
        titulos = [o['title'] for o in c.get('/api/v1/occurrences/nearby/-23.5/-47.4/').json()]
        self.assertEqual(titulos, ['Buraco'])

    def test_historico_de_outra_cidade_vem_vazio(self):
        from history.models import OccurrenceHistory
        OccurrenceHistory.objects.create(
            occurrence=self.camp, user=self.ana, previous_status='open', new_status='open', change_type='edit',
        )
        c = APIClient(); c.force_authenticate(self.maria)
        resp = c.get(f'/api/v1/occurrences/{self.camp.pk}/history/')
        corpo = resp.json()
        itens = corpo['results'] if isinstance(corpo, dict) else corpo
        self.assertEqual(itens, [])


class CidadeNaCriacaoTests(TestCase):
    def setUp(self):
        self.maria = _user('maria', 'Sorocaba', 'SP')
        self.c = APIClient(); self.c.force_authenticate(self.maria)

    def _criar(self, **extra):
        r = self.c.post(LISTA, {'title': 'Buraco', 'description': 'fundo', **extra}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        return Occurrence.objects.get(title='Buraco')

    def test_sem_geocodificacao_herda_a_cidade_do_cadastro(self):
        occ = self._criar()
        self.assertEqual((occ.city, occ.state, occ.city_key), ('Sorocaba', 'SP', 'sorocaba'))

    def test_cidade_geocodificada_tem_prioridade(self):
        occ = self._criar(city='Votorantim', state='sp')
        self.assertEqual((occ.city, occ.state), ('Votorantim', 'SP'))

    def test_claim_de_anonima_herda_a_cidade_do_usuario(self):
        anon = Occurrence.objects.create(title='Anon', anon_id='anon-1')
        r = self.c.post('/api/v1/occurrences/anonymous/claim/', {'anon_id': 'anon-1'}, format='json')
        self.assertEqual(r.json(), {'claimed': 1})
        anon.refresh_from_db()
        self.assertEqual((anon.user, anon.city, anon.state), (self.maria, 'Sorocaba', 'SP'))
