import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('biometrics', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='IdentityVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('audit_snapshot', models.BinaryField()),
                ('snapshot_size', models.PositiveIntegerField()),
                ('verification_method', models.CharField(max_length=12)),
                ('verified_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='identity_verifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.DeleteModel(name='FaceProfile'),
    ]