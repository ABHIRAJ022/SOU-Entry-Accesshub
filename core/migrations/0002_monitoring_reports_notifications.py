from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0001_auditlog')]

    operations = [
        migrations.CreateModel(
            name='SystemHealthEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('component', models.CharField(max_length=40)),
                ('status', models.CharField(max_length=20)),
                ('message', models.TextField(blank=True)),
                ('opened_at', models.DateTimeField(auto_now_add=True)),
                ('recovered_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AccessReportSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], max_length=10, unique=True)),
                ('recipients', models.JSONField(default=list)),
                ('formats', models.JSONField(default=list)),
                ('enabled', models.BooleanField(default=True)),
                ('last_sent_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AccessReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', models.CharField(max_length=10)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField()),
                ('metrics', models.JSONField(default=dict)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='EventNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=64)),
                ('recipients', models.JSONField(default=list)),
                ('payload', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(model_name='systemhealthevent', index=models.Index(fields=['component', '-opened_at'], name='core_system_component_idx')),
    ]