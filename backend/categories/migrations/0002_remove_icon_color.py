from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='icon',
        ),
        migrations.RemoveField(
            model_name='category',
            name='color',
        ),
    ]