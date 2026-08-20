import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0002_tokenaudit')]
    operations = [
        migrations.AddField(model_name='campustoken', name='public_id', field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
        migrations.AddField(model_name='campustoken', name='duration_minutes', field=models.PositiveIntegerField(default=60)),
    ]