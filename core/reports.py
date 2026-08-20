import csv
from io import BytesIO, StringIO

from django.http import HttpResponse
from django.http import JsonResponse
from openpyxl import Workbook

from .models import AuditLog
from dashboard.models import CampusToken


def _rows():
    return AuditLog.objects.select_related('user').values_list('created_at', 'event', 'action', 'status', 'user__email', 'ip_address', 'path')


def audit_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(('Created', 'Event', 'Action', 'Status', 'User', 'IP address', 'Path'))
    writer.writerows(_rows())
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="smart-campus-audit.csv"'
    return response


def audit_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Audit log'
    sheet.append(('Created', 'Event', 'Action', 'Status', 'User', 'IP address', 'Path'))
    for row in _rows():
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="smart-campus-audit.xlsx"'
    return response


def token_rows():
    return CampusToken.objects.select_related('user').values_list('created_at', 'public_id', 'user__email', 'generation', 'duration_minutes', 'expires_at', 'revoked_at', 'used_at')


def token_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(('Created', 'Token ID', 'User', 'Generation', 'Duration minutes', 'Expires', 'Revoked', 'Used'))
    writer.writerows(token_rows())
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="smart-campus-token-usage.csv"'
    return response


def token_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Token usage'
    sheet.append(('Created', 'Token ID', 'User', 'Generation', 'Duration minutes', 'Expires', 'Revoked', 'Used'))
    for row in token_rows():
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="smart-campus-token-usage.xlsx"'
    return response


def audit_json(request):
    rows = AuditLog.objects.select_related('user').values('created_at', 'event', 'action', 'status', 'ip_address', 'path', 'user__email')[:500]
    return JsonResponse({'results': list(rows)})