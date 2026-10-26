from django.core.management.base import BaseCommand

from notifications.services import processar_prazos_e_notificar


class Command(BaseCommand):
    """
    UC-14 — Processar Prazos e Disparar Notificações.

    Uso: python manage.py processar_prazos [--canal email|push]

    Pensado para ser agendado (cron do SO, Task Scheduler, ou futuramente
    Celery beat) rodando periodicamente — ex.: a cada 30 minutos.
    """

    help = 'Verifica prazos de SLA, avisos preventivos e mudanças de status pendentes, disparando notificações (UC-14).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--canal',
            default='email',
            choices=['email', 'push'],
            help='Canal de envio das notificações (default: email).',
        )

    def handle(self, *args, **options):
        resultado = processar_prazos_e_notificar(canal=options['canal'])
        self.stdout.write(self.style.SUCCESS(
            f"Processamento concluído — "
            f"{resultado['prazo_estourado']} prazo(s) estourado(s), "
            f"{resultado['aviso_preventivo']} aviso(s) preventivo(s), "
            f"{resultado['status_change']} mudança(s) de status notificada(s) "
            f"(total: {resultado['total']})."
        ))
