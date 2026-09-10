from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0010_add_tokenscan'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokenscan',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='token_scans', to='dashboard.campuslocation'),
        ),
    ]