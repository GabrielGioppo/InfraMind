import io

from PIL import Image as Image_
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from images.models import Image
from notifications.models import Notificacao
from users.test_perfis import PerfisBase, _user

def _foto(nome='f.png'):
    buf = io.BytesIO()
    Image_.new('RGB', (4, 4), 'red').save(buf, 'PNG')
    return SimpleUploadedFile(nome, buf.getvalue(), content_type='image/png')


class DesignacaoTests(PerfisBase):
    def designar(self, user, occ=None, **corpo):
        self.client.force_authenticate(user)
        return self.client.post(f'/api/v1/occurrences/{(occ or self.poste_soro).pk}/designar/', corpo, format='json')

    def test_gestor_designa_equipe_do_setor_e_cidade(self):
        r = self.designar(self.gestor, equipe=self.equipe.pk)
        self.assertEqual(r.status_code, 200, r.content)
        self.poste_soro.refresh_from_db()
        self.assertEqual(self.poste_soro.equipe_responsavel, self.equipe)
        self.assertTrue(Notificacao.objects.filter(user=self.equipe, tipo='designacao').exists())

    def test_equipe_de_outra_cidade_ou_setor_e_recusada(self):
        outra_cidade = _user('eq2', user_type='equipe_tecnica', setor=self.iluminacao, cidade='Campinas', uf='SP')
        outro_setor = _user('eq3', user_type='equipe_tecnica', setor=self.saneamento, cidade='Sorocaba', uf='SP')
        for p in (outra_cidade, outro_setor):
            self.assertEqual(self.designar(self.gestor, equipe=p.pk).status_code, 400)

    def test_equipe_indisponivel_e_recusada(self):
        self.equipe.disponivel = False
        self.equipe.save()
        self.assertEqual(self.designar(self.gestor, equipe=self.equipe.pk).status_code, 400)

    def test_so_admin_e_gestor_designam_e_so_admin_troca_gestor(self):
        self.assertEqual(self.designar(self.equipe, equipe=self.equipe.pk).status_code, 403)
        self.assertEqual(self.designar(self.cidadao, equipe=self.equipe.pk).status_code, 403)
        self.assertEqual(self.designar(self.gestor, gestor=self.gestor.pk).status_code, 403)
        r = self.designar(self.admin, gestor=self.gestor.pk)
        self.assertEqual(r.status_code, 200, r.content)
        self.poste_soro.refresh_from_db()
        self.assertEqual(self.poste_soro.gestor_responsavel, self.gestor)

    def test_exige_triagem_feita(self):
        self.poste_soro.triagem = 'nova'
        self.poste_soro.save()
        self.assertEqual(self.designar(self.gestor, equipe=self.equipe.pk).status_code, 400)

    def test_gestor_nao_designa_fora_da_area(self):
        self.assertEqual(self.designar(self.gestor, self.poste_camp, equipe=self.equipe.pk).status_code, 404)

    def test_remover_designacao(self):
        self.designar(self.gestor, equipe=self.equipe.pk)
        self.assertEqual(self.designar(self.gestor, equipe=None).status_code, 200)
        self.poste_soro.refresh_from_db()
        self.assertIsNone(self.poste_soro.equipe_responsavel)

    def test_candidatos(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(f'/api/v1/occurrences/{self.poste_soro.pk}/candidatos/')
        self.assertEqual([p['username'] for p in r.json()['equipe']], ['equipe'])
        self.assertEqual([p['username'] for p in r.json()['gestores']], ['gestor'])
        self.client.force_authenticate(self.equipe)
        self.assertEqual(self.client.get(f'/api/v1/occurrences/{self.poste_soro.pk}/candidatos/').status_code, 403)


class EncerramentoTests(PerfisBase):
    def setUp(self):
        super().setUp()
        self.poste_soro.equipe_responsavel = self.equipe
        self.poste_soro.save()
        self.url = f'/api/v1/occurrences/{self.poste_soro.pk}/'

    def foto_resolucao(self, user=None):
        self.client.force_authenticate(user or self.equipe)
        return self.client.post('/api/v1/images/', {'occurrence': self.poste_soro.pk, 'image': _foto(), 'etapa': 'resolucao'},
                                format='multipart')

    def test_equipe_nao_mexe_no_que_nao_foi_designado(self):
        self.poste_soro.equipe_responsavel = None
        self.poste_soro.save()
        self.client.force_authenticate(self.equipe)
        self.assertEqual(self.client.patch(self.url, {'status': 'in_progress'}, format='json').status_code, 403)

    def test_resolvida_exige_parecer_e_foto(self):
        self.client.force_authenticate(self.equipe)
        r = self.client.patch(self.url, {'status': 'resolved'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('parecer_encerramento', r.json())
        self.assertIn('evidencia', r.json())
        self.poste_soro.refresh_from_db()
        self.assertNotEqual(self.poste_soro.status, 'resolved')

    def test_so_parecer_nao_basta(self):
        self.client.force_authenticate(self.equipe)
        r = self.client.patch(self.url, {'status': 'resolved', 'parecer_encerramento': 'Trocada a lâmpada'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('evidencia', r.json())
        self.assertNotIn('parecer_encerramento', r.json())

    def test_resolve_com_parecer_e_foto(self):
        r0 = self.foto_resolucao(); self.assertEqual(r0.status_code, 201, r0.content)
        r = self.client.patch(self.url, {'status': 'resolved', 'parecer_encerramento': 'Lâmpada trocada'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.poste_soro.refresh_from_db()
        self.assertEqual(self.poste_soro.status, 'resolved')
        self.assertEqual(self.poste_soro.parecer_encerramento, 'Lâmpada trocada')
        self.assertIsNotNone(self.poste_soro.resolved_at)

    def test_gestor_tambem_precisa_da_evidencia(self):
        self.client.force_authenticate(self.gestor)
        self.assertEqual(self.client.patch(self.url, {'status': 'resolved', 'parecer_encerramento': 'ok'}, format='json').status_code, 400)

    def test_foto_de_resolucao_so_da_equipe_designada_gestor_ou_admin(self):
        self.assertEqual(self.foto_resolucao(self.cidadao).status_code, 400)
        outra = _user('eq2', user_type='equipe_tecnica', setor=self.iluminacao, cidade='Sorocaba', uf='SP')
        self.assertEqual(self.foto_resolucao(outra).status_code, 400)
        self.assertEqual(self.foto_resolucao(self.gestor).status_code, 201)
        self.assertEqual(Image.objects.filter(etapa='resolucao').count(), 1)

    def test_cidadao_nao_escreve_parecer_nem_designacao(self):
        self.client.force_authenticate(self.cidadao)
        self.client.patch(self.url, {'parecer_encerramento': 'x', 'equipe_responsavel': self.cidadao.pk}, format='json')
        self.poste_soro.refresh_from_db()
        self.assertEqual(self.poste_soro.parecer_encerramento, '')
        self.assertEqual(self.poste_soro.equipe_responsavel, self.equipe)


class AvisosETDisponibilidadeTests(PerfisBase):
    def test_nova_ocorrencia_avisa_gestores_da_area(self):
        from notifications.services import notificar_nova_ocorrencia
        notificar_nova_ocorrencia(self.poste_soro)
        self.assertTrue(Notificacao.objects.filter(user=self.gestor, tipo='nova_ocorrencia').exists())
        self.assertFalse(Notificacao.objects.filter(user=self.outro_gestor, tipo='nova_ocorrencia').exists())
        self.assertFalse(Notificacao.objects.filter(user=self.gestor_campinas, tipo='nova_ocorrencia').exists())

    def test_encaminhamento_avisa_o_gestor_do_novo_setor(self):
        self.esgoto_soro.triagem = 'nova'
        self.esgoto_soro.save()
        self.client.force_authenticate(self.admin)
        r = self.client.post(f'/api/v1/occurrences/{self.esgoto_soro.pk}/triagem/',
                             {'acao': 'aprovar', 'importance_color': 'red', 'prazo_definido': '2099-01-01T10:00:00Z'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Notificacao.objects.filter(user=self.outro_gestor, tipo='encaminhamento').exists())

    def test_disponibilidade_via_me(self):
        self.client.force_authenticate(self.equipe)
        r = self.client.patch('/api/v1/users/me/', {'disponivel': False}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.equipe.refresh_from_db()
        self.assertFalse(self.equipe.disponivel)
