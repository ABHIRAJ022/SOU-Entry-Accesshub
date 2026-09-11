from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0012_tokenscan_custom_location'), ('accounts', '0006_user_location_sharing_enabled')]

    operations = [
        migrations.AddField(model_name='tokenscan', name='latitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='tokenscan', name='longitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='tokenscan', name='accuracy', field=models.FloatField(blank=True, null=True)),
        migrations.CreateModel(
            name='UserLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy', models.FloatField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='latest_location', to=settings.AUTH_USER_MODEL)),
            ],
            options={'indexes': [models.Index(fields=['recorded_at'], name='dashboard_u_recorded_6c3fb4_idx')]},
        ),
        migrations.CreateModel(
            name='LocationHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy', models.FloatField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='location_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-recorded_at',), 'indexes': [
                models.Index(fields=['user', '-recorded_at'], name='dashboard_l_user_id_7f5ef1_idx'),
                models.Index(fields=['recorded_at'], name='dashboard_l_recorded_3ce6e8_idx'),
            ]},
        ),
    ]
