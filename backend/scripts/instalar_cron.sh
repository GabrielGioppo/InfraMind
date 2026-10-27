#!/usr/bin/env bash
# Agenda a rotina de prazos do UC-14 (manage.py processar_prazos) no cron do usuário.
#
# Uso (Linux/Mac), dentro de backend/:
#     bash scripts/instalar_cron.sh              # a cada 30 minutos (padrão)
#     bash scripts/instalar_cron.sh "0 * * * *"  # outra frequência (formato do cron)
#     bash scripts/instalar_cron.sh --remover    # tira o agendamento
#
# É seguro rodar mais de uma vez: o agendamento anterior é substituído.

set -euo pipefail

MARCADOR="# InfraMind processar_prazos"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
  PYTHON="$BACKEND_DIR/venv/bin/python"
elif [ -x "$BACKEND_DIR/../venv/bin/python" ]; then
  PYTHON="$(cd "$BACKEND_DIR/.." && pwd)/venv/bin/python"
else
  PYTHON="$(command -v python3)"
fi

# Crontab atual sem a linha antiga do InfraMind (se existir).
atual="$( (crontab -l 2>/dev/null || true) | grep -vF "$MARCADOR" || true )"

if [ "${1:-}" = "--remover" ]; then
  printf '%s\n' "$atual" | crontab -
  echo "Agendamento do InfraMind removido."
  exit 0
fi

AGENDA="${1:-*/30 * * * *}"
LINHA="$AGENDA cd \"$BACKEND_DIR\" && \"$PYTHON\" manage.py processar_prazos >> \"$BACKEND_DIR/processar_prazos.log\" 2>&1 $MARCADOR"

printf '%s\n%s\n' "$atual" "$LINHA" | sed '/^$/d' | crontab -
echo "Agendado: $LINHA"
echo "Saída da rotina em: $BACKEND_DIR/processar_prazos.log"
