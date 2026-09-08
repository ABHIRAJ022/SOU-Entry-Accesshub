from django.apps import AppConfig


class BiometricsConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'biometrics'
