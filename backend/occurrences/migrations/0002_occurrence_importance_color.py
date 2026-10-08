from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('occurrences', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='importance_color',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=10,
                choices=[
                    ('green', 'Normal'),
                    ('yellow', 'Um Pouco Importante'),
                    ('red', 'Importante'),
                ],
                verbose_name='Nível de Importância',
                help_text='Verde = Normal | Amarelo = Um pouco importante | Vermelho = Importante',
            ),
        ),
    ]