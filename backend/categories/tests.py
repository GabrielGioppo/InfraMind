from unittest.mock import patch

from rest_framework.test import APITestCase

from categories.models import Category, Subcategory
from users.models import User


class PermissaoDasCategoriasTests(APITestCase):
    """Leitura é pública; escrever (criar/editar/apagar) é só do administrador."""

    def setUp(self):
        self.cat = Category.objects.create(name='Iluminação', description='Postes e lâmpadas')
        self.cidadao = User.objects.create_user(username='cid', email='c@x.com', password='Senha-12345')
        self.admin = User.objects.create_user(
            username='adm', email='a@x.com', password='Senha-12345', user_type='admin', is_staff=True,
        )

    def test_leitura_publica(self):
        self.assertEqual(self.client.get('/api/v1/categories/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/categories/{self.cat.pk}/').status_code, 200)

    def test_anonimo_nao_escreve(self):
        self.assertIn(self.client.post('/api/v1/categories/', {'name': 'X', 'description': 'y'}).status_code, (401, 403))
        self.assertIn(self.client.delete(f'/api/v1/categories/{self.cat.pk}/').status_code, (401, 403))

    def test_cidadao_nao_escreve(self):
        self.client.force_authenticate(self.cidadao)
        self.assertEqual(self.client.post('/api/v1/categories/', {'name': 'X', 'description': 'y'}).status_code, 403)
        self.assertEqual(self.client.patch(f'/api/v1/categories/{self.cat.pk}/', {'name': 'Z'}).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/categories/{self.cat.pk}/').status_code, 403)
        self.assertTrue(Category.objects.filter(pk=self.cat.pk, name='Iluminação').exists())

    def test_admin_escreve(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/v1/categories/', {'name': 'Praças', 'description': 'Áreas verdes'}).status_code, 201)
        self.assertEqual(self.client.patch(f'/api/v1/categories/{self.cat.pk}/', {'description': 'Novo'}).status_code, 200)
        self.assertEqual(self.client.delete(f'/api/v1/categories/{self.cat.pk}/').status_code, 204)


class SubcategoriasTests(APITestCase):
    def setUp(self):
        self.setor = Category.objects.get(name='Saneamento básico')
        self.sub = Subcategory.objects.get(category=self.setor, name='Esgoto entupido ou vazando')
        self.outra = Category.objects.get(name='Iluminação pública')
        self.cidadao = User.objects.create_user(username='cid', email='c@x.com', password='Senha-12345')
        self.admin = User.objects.create_user(
            username='adm', email='a@x.com', password='Senha-12345', user_type='admin', is_staff=True,
        )

    def test_catalogo_padrao_carregado(self):
        self.assertGreaterEqual(Category.objects.filter(subcategories__isnull=False).distinct().count(), 12)
        self.assertTrue(Subcategory.objects.filter(category__name='Iluminação pública', name='Poste caído').exists())

    def test_lista_de_setores_traz_subcategorias_ativas(self):
        Subcategory.objects.filter(pk=self.sub.pk).update(is_active=False)
        dados = self.client.get('/api/v1/categories/').json()
        dados = dados if isinstance(dados, list) else dados['results']
        setor = next(c for c in dados if c['id'] == self.setor.pk)
        self.assertNotIn(self.sub.pk, [s['id'] for s in setor['subcategories']])
        self.client.force_authenticate(self.admin)
        dados = self.client.get('/api/v1/categories/').json()
        dados = dados if isinstance(dados, list) else dados['results']
        setor = next(c for c in dados if c['id'] == self.setor.pk)
        self.assertIn(self.sub.pk, [s['id'] for s in setor['subcategories']])

    def test_filtra_subcategorias_por_setor(self):
        r = self.client.get(f'/api/v1/categories/subcategories/?category={self.outra.pk}').json()
        r = r if isinstance(r, list) else r['results']
        self.assertTrue(r and all(s['category'] == self.outra.pk for s in r))

    def test_so_admin_escreve_subcategoria(self):
        corpo = {'category': self.setor.pk, 'name': 'Tubulação rompida'}
        self.assertIn(self.client.post('/api/v1/categories/subcategories/', corpo).status_code, (401, 403))
        self.client.force_authenticate(self.cidadao)
        self.assertEqual(self.client.post('/api/v1/categories/subcategories/', corpo).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/v1/categories/subcategories/', corpo).status_code, 201)
        # nome repetido no mesmo setor (sem diferenciar maiúsculas) é recusado
        r = self.client.post('/api/v1/categories/subcategories/', {**corpo, 'name': 'tubulação ROMPIDA'})
        self.assertEqual(r.status_code, 400)
        # mas o mesmo nome em outro setor é permitido
        r = self.client.post('/api/v1/categories/subcategories/', {'category': self.outra.pk, 'name': 'Tubulação rompida'})
        self.assertEqual(r.status_code, 201)

    def test_admin_edita_e_apaga_subcategoria(self):
        self.client.force_authenticate(self.admin)
        url = f'/api/v1/categories/subcategories/{self.sub.pk}/'
        self.assertEqual(self.client.patch(url, {'is_active': False}).status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 204)


class OcorrenciaComSubcategoriaTests(APITestCase):
    def setUp(self):
        self.setor = Category.objects.get(name='Iluminação pública')
        self.sub = Subcategory.objects.get(category=self.setor, name='Poste caído')
        self.outro_setor = Category.objects.get(name='Saneamento básico')
        self.user = User.objects.create_user(
            username='cid', email='c@x.com', password='Senha-12345', cidade='Sorocaba', uf='SP',
        )
        self.client.force_authenticate(self.user)

    def _criar(self, **extra):
        corpo = {'title': 'Poste na calçada', 'description': 'Poste caído bloqueando a calçada', 'category': self.setor.pk,
                 'latitude': -23.5, 'longitude': -47.4, 'status': 'open', **extra}
        with patch('occurrences.views.analyze_occurrence_description_and_photo', return_value={
                'descricao_final': corpo['description'], 'original_description': corpo['description'],
                'status': 'ok', 'sugestao': ''}):
            return self.client.post('/api/v1/occurrences/', corpo, format='json')

    def test_cria_com_setor_e_subcategoria(self):
        r = self._criar(subcategory=self.sub.pk)
        self.assertEqual(r.status_code, 201, r.content)
        occ = r.json()['occurrence']
        self.assertEqual(occ['subcategory'], self.sub.pk)
        self.assertEqual(occ['subcategory_details']['name'], 'Poste caído')

    def test_subcategoria_de_outro_setor_e_recusada(self):
        r = self._criar(subcategory=Subcategory.objects.filter(category=self.outro_setor).first().pk)
        self.assertEqual(r.status_code, 400)
        self.assertIn('subcategory', r.json())

    def test_so_subcategoria_define_o_setor(self):
        r = self._criar(subcategory=self.sub.pk, category=None)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['occurrence']['category'], self.setor.pk)

    def test_trocar_o_setor_limpa_a_subcategoria(self):
        occ_id = self._criar(subcategory=self.sub.pk).json()['occurrence']['id']
        r = self.client.patch(f'/api/v1/occurrences/{occ_id}/', {'category': self.outro_setor.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(r.json()['subcategory'])
