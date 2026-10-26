import json
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from images.models import Image
from occurrences.models import Occurrence
from scripts.backup import fazer_backup
from users.models import User


class BackupTests(TestCase):
    """RNF09: o backup tem os dados do banco e as imagens, e dá para restaurar."""

    def test_backup_gera_dados_e_media_e_restaura(self):
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / 'media_origem'
            destino = Path(tmp) / 'backups'

            with override_settings(MEDIA_ROOT=str(media)):
                user = User.objects.create_user(
                    username='joao', email='joao@exemplo.com', password='x-12345-y',
                )
                occ = Occurrence.objects.create(title='Poste caído', user=user)
                img = Image(occurrence=occ, user=user)
                img.image.save('foto.jpg', ContentFile(b'conteudo-da-foto'), save=True)

                pasta = fazer_backup(destino)

            dados = json.loads((pasta / 'dados.json').read_text(encoding='utf-8'))
            modelos = {item['model'] for item in dados}
            self.assertTrue({'users.user', 'occurrences.occurrence', 'images.image'} <= modelos)
            self.assertNotIn('contenttypes.contenttype', modelos)
            copiada = pasta / 'media' / img.image.name
            self.assertEqual(copiada.read_bytes(), b'conteudo-da-foto')

            # Restauração: apaga tudo e recarrega do dump.
            Image.objects.all().delete()
            Occurrence.objects.all().delete()
            User.objects.all().delete()
            call_command('loaddata', str(pasta / 'dados.json'), verbosity=0)

            self.assertEqual(Occurrence.objects.get().title, 'Poste caído')
            self.assertEqual(User.objects.get().email, 'joao@exemplo.com')
            self.assertEqual(Image.objects.count(), 1)
