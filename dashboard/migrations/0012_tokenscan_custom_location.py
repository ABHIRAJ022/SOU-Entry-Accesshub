from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0011_tokenscan_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokenscan',
            name='custom_location',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
