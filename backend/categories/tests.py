from rest_framework.test import APITestCase

from categories.models import Category
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
