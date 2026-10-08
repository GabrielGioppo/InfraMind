from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('occurrences', '0002_occurrence_importance_color'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OccurrenceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_status', models.CharField(blank=True, max_length=20, null=True)),
                ('new_status', models.CharField(blank=True, max_length=20, null=True)),
                ('change_type', models.CharField(choices=[('status', 'Mudança de Status'), ('priority', 'Mudança de Prioridade'), ('edit', 'Edição de Dados')], default='status', max_length=20)),
                ('observation', models.TextField(blank=True, null=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('occurrence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='history', to='occurrences.occurrence')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='occurrence_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-changed_at']},
        ),
    ]
