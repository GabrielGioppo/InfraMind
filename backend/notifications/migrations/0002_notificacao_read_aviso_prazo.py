from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificacao",
            name="read",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="notificacao",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("prazo_estourado", "Prazo Estourado"),
                    ("aviso_prazo", "Aviso de Proximidade de Prazo"),
                    ("status_change", "Mudança de Status"),
                    ("geral", "Geral"),
                ],
                default="geral",
                max_length=20,
            ),
        ),
    ]
