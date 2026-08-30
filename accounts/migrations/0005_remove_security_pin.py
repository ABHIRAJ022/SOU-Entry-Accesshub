from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_user_profile_photo')]

    operations = [
        migrations.RemoveField(
            model_name='user', name='security_pin_hash',
        ),
    ]
