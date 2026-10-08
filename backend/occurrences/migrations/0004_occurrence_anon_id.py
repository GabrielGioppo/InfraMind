from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('occurrences', '0003_occurrence_urgency_ai_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='occurrence',
            name='anon_id',
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='occurrence',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='occurrences',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
