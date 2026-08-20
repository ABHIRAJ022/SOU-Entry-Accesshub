from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_user_security_pin_hash')]
    operations = [migrations.AddField(
        model_name='user', name='profile_photo',
        field=models.BinaryField(blank=True, null=True),
    )]