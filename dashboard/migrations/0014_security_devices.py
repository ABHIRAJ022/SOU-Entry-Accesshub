from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0013_location_tracking')]

    operations = [
        migrations.CreateModel(
            name='SecurityDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=80, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('gate', models.CharField(max_length=120)),
                ('building', models.CharField(blank=True, max_length=120)),
                ('access_zone', models.CharField(blank=True, max_length=120)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('DISABLED', 'Disabled'), ('MAINTENANCE', 'Maintenance')], default='ACTIVE', max_length=16)),
                ('credential_hash', models.CharField(blank=True, max_length=128)),
                ('last_seen', models.DateTimeField(blank=True, null=True)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('allowed_radius_meters', models.PositiveIntegerField(default=150)),
                ('assigned_security_staff', models.ManyToManyField(blank=True, related_name='security_devices', to=settings.AUTH_USER_MODEL)),
                ('campus_location', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='security_devices', to='dashboard.campuslocation')),
            ],
        ),
        migrations.AddField(model_name='tokenscan', name='device', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='token_scans', to='dashboard.securitydevice')),
        migrations.AddField(model_name='tokenscan', name='resolved_access_zone', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='tokenscan', name='resolved_building', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='tokenscan', name='resolved_gate', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='tokenscan', name='gps_status', field=models.CharField(default='not_provided', max_length=16)),
    ]