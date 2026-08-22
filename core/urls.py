from django.urls import path
from django.contrib.auth.decorators import user_passes_test
from . import reports

admin_only = user_passes_test(lambda user: user.is_authenticated and user.role == 'ADMIN' and user.is_superuser)
urlpatterns = [
	path('reports/audit.csv', admin_only(reports.audit_csv), name='audit_csv'),
	path('reports/audit.xlsx', admin_only(reports.audit_xlsx), name='audit_xlsx'),
	path('reports/audit.json', admin_only(reports.audit_json), name='audit_json'),
	path('reports/tokens.csv', admin_only(reports.token_csv), name='token_csv'),
	path('reports/tokens.xlsx', admin_only(reports.token_xlsx), name='token_xlsx'),
]
from django.urls import path
from .views import health_check
urlpatterns = [path('health/', health_check, name='health')]
