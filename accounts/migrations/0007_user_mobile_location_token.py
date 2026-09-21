from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0006_user_location_sharing_enabled')]

    operations = [
        migrations.AddField(
            model_name='user', name='mobile_location_token_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]