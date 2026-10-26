"""
Backup do InfraMind (RNF09).

Gera uma pasta com data e hora contendo:
  - dados.json : todos os dados do banco (manage.py dumpdata)
  - media/     : cópia das imagens enviadas pelos usuários

Uso (dentro de backend/, com o venv ativado):

    python scripts/backup.py                     # grava em backend/backups/
    python scripts/backup.py --destino /mnt/hd   # grava em outra pasta

Para agendar todo dia às 03:00 (Linux/Mac), adicione ao crontab:

    0 3 * * * cd /caminho/InfraMind/backend && venv/bin/python scripts/backup.py

Como restaurar: veja a seção "Backup e restauração" do README.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

# Tabelas recriadas automaticamente pelo Django; restaurá-las só causa conflito.
EXCLUIR_DO_DUMP = ['contenttypes', 'auth.permission', 'admin.logentry', 'sessions']


def fazer_backup(destino: Path) -> Path:
    """Cria a pasta do backup dentro de `destino` e devolve o caminho dela."""
    pasta = destino / f'backup_{datetime.now():%Y%m%d_%H%M%S}'
    pasta.mkdir(parents=True, exist_ok=False)

    arquivo_dados = pasta / 'dados.json'
    with open(arquivo_dados, 'w', encoding='utf-8') as f:
        call_command(
            'dumpdata',
            exclude=EXCLUIR_DO_DUMP,
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=f,
        )

    media_root = Path(settings.MEDIA_ROOT)
    if media_root.is_dir():
        shutil.copytree(media_root, pasta / 'media')
    else:
        print(f'Aviso: pasta de mídia não encontrada ({media_root}); nada a copiar.')

    return pasta


def main() -> int:
    parser = argparse.ArgumentParser(description='Backup do banco de dados e da pasta media/.')
    parser.add_argument(
        '--destino', type=Path, default=BACKEND_DIR / 'backups',
        help='Pasta onde o backup será criado (padrão: backend/backups).',
    )
    args = parser.parse_args()

    try:
        pasta = fazer_backup(args.destino)
    except Exception as e:
        print(f'Falha no backup: {e}', file=sys.stderr)
        return 1

    print(f'Backup concluído: {pasta}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
