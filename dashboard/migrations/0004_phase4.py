import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0003_campustoken_phase3')]
    operations = [
        migrations.AddField(model_name='campustoken', name='used_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='campustoken', name='used_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='validated_tokens', to=settings.AUTH_USER_MODEL)),
        migrations.CreateModel(
            name='CampusLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('category', models.CharField(choices=[('LIBRARY', 'Library'), ('SECURITY_GATE', 'Security Gate'), ('ADMIN_BLOCK', 'Admin Block'), ('HOSTEL', 'Hostel'), ('CANTEEN', 'Canteen'), ('DEPARTMENT', 'Department'), ('SPORTS_COMPLEX', 'Sports Complex'), ('MEDICAL_CENTER', 'Medical Center'), ('LAB', 'Lab'), ('AUDITORIUM', 'Auditorium')], max_length=20)),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('description', models.TextField(blank=True)),
                ('building_code', models.CharField(blank=True, max_length=32)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='campus_locations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TokenNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(max_length=16)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('token', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='dashboard.campustoken')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('token', 'kind'), name='unique_token_notification')]},
        ),
    ]