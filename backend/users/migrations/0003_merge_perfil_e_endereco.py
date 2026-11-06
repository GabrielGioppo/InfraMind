from django.db import migrations


class Migration(migrations.Migration):
    """Junta a ponta do cadastro com CPF/endereço e a da foto de perfil."""

    dependencies = [
        ('users', '0002_cpf_e_endereco'),
        ('users', '0002_user_cpf_user_profile_picture'),
    ]

    operations = []
