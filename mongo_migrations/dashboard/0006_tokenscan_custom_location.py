from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0005_location_category_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='tokenscan',
            name='custom_location',
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
