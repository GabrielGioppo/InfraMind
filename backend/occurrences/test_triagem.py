from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from categories.models import Category, Subcategory
from history.models import OccurrenceHistory
from logs.models import Log
from occurrences.models import Occurrence
from occurrences.visibility import visible_occurrences
from users.models import User

SENHA = 'Senha-12345'


def _user(nome, **extra):
    return User.objects.create_user(username=nome, email=f'{nome}@x.com', password=SENHA, **extra)


class TriagemTests(APITestCase):
    def setUp(self):
        self.ilum = Category.objects.get(name='Iluminação pública')
        self.sanea = Category.objects.get(name='Saneamento básico')
        self.sub_sanea = Subcategory.objects.filter(category=self.sanea).first()
        self.admin = _user('adm', user_type='admin')
        self.gestor = _user('gestor', user_type='gestor', setor=self.ilum, cidade='Sorocaba', uf='SP')
        self.equipe = _user('equipe', user_type='equipe_tecnica', setor=self.ilum, cidade='Sorocaba', uf='SP')
        self.cidadao = _user('cid', cidade='Sorocaba', uf='SP')
        self.occ = Occurrence.objects.create(
            title='Poste caído', user=self.cidadao, category=self.ilum, city='Sorocaba', state='SP')
        self.prazo = (timezone.now() + timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')

    def url(self, occ=None):
        return f'/api/v1/occurrences/{(occ or self.occ).pk}/triagem/'

    # ── padrão ────────────────────────────────────────────────────
    def test_ocorrencia_nasce_nova(self):
        self.assertEqual(self.occ.triagem, 'nova')

    def test_filtro_por_triagem_na_lista(self):
        Occurrence.objects.create(title='Outra', user=self.cidadao, category=self.ilum, city='Sorocaba', state='SP', triagem='triada')
        self.client.force_authenticate(self.gestor)
        r = self.client.get('/api/v1/occurrences/?triagem=nova').json()
        r = r if isinstance(r, list) else r['results']
        self.assertEqual([o['title'] for o in r], ['Poste caído'])

    # ── aprovar ───────────────────────────────────────────────────
    def test_gestor_aprova_com_importancia_e_prazo(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': self.prazo}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.occ.refresh_from_db()
        self.assertEqual((self.occ.triagem, self.occ.importance_color, self.occ.triagem_por_id),
                         ('triada', 'red', self.gestor.pk))
        self.assertIsNotNone(self.occ.prazo_definido)
        self.assertIsNotNone(self.occ.triagem_em)
        self.assertEqual(self.occ.status, 'open')   # a triagem não mexe no status
        self.assertGreater(self.occ.priority, 0)
        h = OccurrenceHistory.objects.filter(occurrence=self.occ).first()
        self.assertIn('Triagem aprovada', h.observation)
        self.assertTrue(Log.objects.filter(action='update', object_id=self.occ.pk).exists())

    def test_aprovar_exige_importancia_e_prazo_no_futuro(self):
        self.client.force_authenticate(self.gestor)
        self.assertEqual(self.client.post(self.url(), {'prazo_definido': self.prazo}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url(), {'importance_color': 'red'}, format='json').status_code, 400)
        passado = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        r = self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': passado}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('prazo_definido', r.json())
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.triagem, 'nova')

    def test_usa_importancia_e_prazo_que_a_ocorrencia_ja_tem(self):
        Occurrence.objects.filter(pk=self.occ.pk).update(
            importance_color='yellow', prazo_definido=timezone.now() + timedelta(days=2))
        self.client.force_authenticate(self.gestor)
        self.assertEqual(self.client.post(self.url(), {}, format='json').status_code, 200)

    def test_encaminha_para_outro_setor(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url(), {'importance_color': 'yellow', 'prazo_definido': self.prazo,
                                          'category': self.sanea.pk, 'subcategory': self.sub_sanea.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.occ.refresh_from_db()
        self.assertEqual((self.occ.category_id, self.occ.subcategory_id), (self.sanea.pk, self.sub_sanea.pk))
        self.assertIn('encaminhada de Iluminação pública para Saneamento básico',
                      OccurrenceHistory.objects.filter(occurrence=self.occ).first().observation)

    def test_trocar_so_o_setor_limpa_a_subcategoria(self):
        Occurrence.objects.filter(pk=self.occ.pk).update(subcategory=Subcategory.objects.filter(category=self.ilum).first())
        self.client.force_authenticate(self.admin)
        self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': self.prazo, 'category': self.sanea.pk}, format='json')
        self.occ.refresh_from_db()
        self.assertIsNone(self.occ.subcategory_id)

    def test_subcategoria_de_outro_setor_e_recusada(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': self.prazo,
                                          'category': self.ilum.pk, 'subcategory': self.sub_sanea.pk}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_gestor_perde_de_vista_o_que_encaminhou(self):
        self.client.force_authenticate(self.gestor)
        r = self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': self.prazo, 'category': self.sanea.pk}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(self.occ, visible_occurrences(self.gestor))

    # ── rejeitar ──────────────────────────────────────────────────
    def test_rejeitar_exige_motivo_e_encerra(self):
        self.client.force_authenticate(self.gestor)
        self.assertEqual(self.client.post(self.url(), {'acao': 'rejeitar'}, format='json').status_code, 400)
        r = self.client.post(self.url(), {'acao': 'rejeitar', 'observacao': 'Conteúdo falso'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.occ.refresh_from_db()
        self.assertEqual((self.occ.triagem, self.occ.status, self.occ.triagem_obs), ('rejeitada', 'closed', 'Conteúdo falso'))
        h = OccurrenceHistory.objects.filter(occurrence=self.occ).first()
        self.assertEqual((h.previous_status, h.new_status), ('open', 'closed'))

    # ── regras ────────────────────────────────────────────────────
    def test_so_admin_e_gestor_triam(self):
        corpo = {'importance_color': 'red', 'prazo_definido': self.prazo}
        self.assertEqual(self.client.post(self.url(), corpo, format='json').status_code, 401)
        for u in (self.cidadao, self.equipe):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.post(self.url(), corpo, format='json').status_code, 403, u.username)
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.triagem, 'nova')

    def test_gestor_nao_tria_ocorrencia_de_outro_setor_ou_cidade(self):
        outra = Occurrence.objects.create(title='Esgoto', user=self.cidadao, category=self.sanea, city='Sorocaba', state='SP')
        longe = Occurrence.objects.create(title='Poste Campinas', user=self.cidadao, category=self.ilum, city='Campinas', state='SP')
        self.client.force_authenticate(self.gestor)
        for occ in (outra, longe):
            r = self.client.post(self.url(occ), {'importance_color': 'red', 'prazo_definido': self.prazo}, format='json')
            self.assertEqual(r.status_code, 404)

    def test_nao_tria_duas_vezes(self):
        self.client.force_authenticate(self.gestor)
        corpo = {'importance_color': 'red', 'prazo_definido': self.prazo}
        self.assertEqual(self.client.post(self.url(), corpo, format='json').status_code, 200)
        self.assertEqual(self.client.post(self.url(), corpo, format='json').status_code, 400)

    def test_triagem_nao_muda_por_patch(self):
        self.client.force_authenticate(self.admin)
        self.client.patch(f'/api/v1/occurrences/{self.occ.pk}/', {'triagem': 'triada'}, format='json')
        self.occ.refresh_from_db()
        self.assertEqual(self.occ.triagem, 'nova')

    def test_equipe_so_ve_o_que_foi_aprovado(self):
        self.assertNotIn(self.occ, visible_occurrences(self.equipe))
        self.client.force_authenticate(self.gestor)
        self.client.post(self.url(), {'importance_color': 'red', 'prazo_definido': self.prazo}, format='json')
        self.assertIn(self.occ, visible_occurrences(self.equipe))

    def test_ocorrencias_antigas_foram_classificadas_pela_migration(self):
        from django.apps import apps
        import importlib
        mig = importlib.import_module('occurrences.migrations.0016_triagem_das_ocorrencias_existentes')
        novas = Occurrence.objects.create(title='Aberta sem nada', user=self.cidadao)
        andamento = Occurrence.objects.create(title='Em andamento', user=self.cidadao, status='in_progress')
        definida = Occurrence.objects.create(title='Com importância', user=self.cidadao, importance_color='red')
        Occurrence.objects.update(triagem='nova')
        mig.marcar_existentes(apps, None)
        for o in (novas, andamento, definida):
            o.refresh_from_db()
        self.assertEqual((novas.triagem, andamento.triagem, definida.triagem), ('nova', 'triada', 'triada'))
