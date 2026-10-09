from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0002_log_device'),
    ]

    operations = [
        migrations.AlterField(
            model_name='log',
            name='action',
            field=models.CharField(
                choices=[
                    ('create', 'Criar'),
                    ('update', 'Atualizar'),
                    ('delete', 'Deletar'),
                    ('validate', 'Validar'),
                    ('status_change', 'Mudança de Status'),
                    ('login', 'Login'),
                    ('notification_sent', 'Notificação Enviada'),
                    ('notification_failed', 'Falha no Envio de Notificação'),
                ],
                max_length=20,
            ),
        ),
    ]
