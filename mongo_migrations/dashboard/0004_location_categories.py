from django.db import migrations, models
import django_mongodb_backend.fields


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0002_remove_campustoken_token_has_exactly_one_owner"),
        ("dashboard", "0003_remove_campustoken_token_has_exactly_one_owner"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campuslocation",
            name="category",
            field=models.CharField(max_length=50),
        ),
        migrations.CreateModel(
            name="LocationCategory",
            fields=[
                (
                    "id",
                    django_mongodb_backend.fields.ObjectIdAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=80, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("name",),
                "verbose_name": "Campus location category",
                "verbose_name_plural": "Campus location categories",
            },
        ),
    ]
