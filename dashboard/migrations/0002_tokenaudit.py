import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0001_initial')]
    operations = [migrations.CreateModel(
        name='TokenAudit',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('snapshot', models.BinaryField()),
            ('snapshot_size', models.PositiveIntegerField()),
            ('verification_method', models.CharField(max_length=12)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('token', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='audit', to='dashboard.campustoken')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='token_audits', to=settings.AUTH_USER_MODEL)),
        ],
    )]