from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_user_is_approved_by_super_admin_branch_user_branch')]
    operations = [migrations.AddField(
        model_name='user', name='security_pin_hash',
        field=models.CharField(blank=True, max_length=128),
    )]