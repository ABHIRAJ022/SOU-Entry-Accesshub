from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django_mongodb_backend.fields


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0006_tokenscan_custom_location'), ('accounts', '0002_user_location_sharing_enabled')]

    operations = [
        migrations.AddField(model_name='tokenscan', name='latitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='tokenscan', name='longitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='tokenscan', name='accuracy', field=models.FloatField(blank=True, null=True)),
        migrations.CreateModel(
            name='UserLocation',
            fields=[
                ('id', django_mongodb_backend.fields.ObjectIdAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy', models.FloatField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='latest_location', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LocationHistory',
            fields=[
                ('id', django_mongodb_backend.fields.ObjectIdAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy', models.FloatField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='location_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-recorded_at',)},
        ),
    ]
