from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='device',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
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
                ],
                max_length=20,
            ),
        ),
    ]
