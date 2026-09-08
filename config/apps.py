from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig
from django.contrib.sites.apps import SitesConfig
from allauth.account.apps import AccountConfig
from allauth.socialaccount.apps import SocialAccountConfig


class MongoAdminConfig(AdminConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoAuthConfig(AuthConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoSitesConfig(SitesConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoAccountConfig(AccountConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoSocialAccountConfig(SocialAccountConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
