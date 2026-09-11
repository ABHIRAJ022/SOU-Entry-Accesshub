from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0005_remove_security_pin')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='location_sharing_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
