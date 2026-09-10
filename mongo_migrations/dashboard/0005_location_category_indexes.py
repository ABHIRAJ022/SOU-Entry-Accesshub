from django.db import migrations


def ensure_location_category_indexes(apps, schema_editor):
    database = schema_editor.connection.get_database()
    collection_name = 'dashboard_locationcategory'
    if collection_name not in database.list_collection_names():
        return
    collection = database.get_collection(collection_name)
    collection.create_index('code', unique=True)
    collection.create_index('name', unique=True)


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0004_location_categories'),
    ]

    operations = [
        migrations.RunPython(ensure_location_category_indexes, migrations.RunPython.noop),
    ]
