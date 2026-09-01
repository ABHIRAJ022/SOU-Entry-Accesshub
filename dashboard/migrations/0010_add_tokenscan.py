# Generated manual migration: add TokenScan model
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_alter_guesttokenrequest_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='TokenScan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('scanned_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='token_scans', to='accounts.user')),
                ('token', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='dashboard.campustoken')),
            ],
            options={
                'ordering': ['-scanned_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='tokenscan',
            constraint=models.UniqueConstraint(fields=('token', 'scanned_by'), name='unique_token_scan_per_user'),
        ),
    ]
