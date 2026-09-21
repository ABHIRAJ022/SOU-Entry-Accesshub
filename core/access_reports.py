import csv
from datetime import timedelta
from io import BytesIO, StringIO

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Count
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from dashboard.models import CampusToken, GuestTokenRequest, TokenScan, UserLocation
from .models import AccessReport


def metrics_for_window(starts_at, ends_at):
    scans = TokenScan.objects.filter(scanned_at__gte=starts_at, scanned_at__lt=ends_at)
    return {
        'entries': scans.count(),
        'exits': 0,
        'active_users': UserLocation.objects.filter(recorded_at__gte=starts_at, recorded_at__lt=ends_at).values('user_id').distinct().count(),
        'visitors': scans.filter(token__guest_request__isnull=False).count(),
        'expired_tokens': CampusToken.objects.filter(expires_at__gte=starts_at, expires_at__lt=ends_at).count(),
        'rejected_or_failed_scans': 0,
        'suspicious_events': scans.filter(gps_status='failed').count(),
        'overstays': 0,
        'scans_by_gate': list(scans.values('resolved_gate').annotate(total=Count('id')).order_by('-total')),
    }


def build_artifacts(metrics, formats):
    artifacts = []
    if 'csv' in formats:
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(('Metric', 'Value'))
        for key, value in metrics.items():
            if isinstance(value, list):
                continue
            writer.writerow((key, value))
        artifacts.append(('access-report.csv', stream.getvalue().encode(), 'text/csv'))
    if 'xlsx' in formats:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Access report'
        sheet.append(('Metric', 'Value'))
        for key, value in metrics.items():
            if not isinstance(value, list):
                sheet.append((key, value))
        stream = BytesIO()
        workbook.save(stream)
        artifacts.append(('access-report.xlsx', stream.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
    if 'pdf' in formats:
        stream = BytesIO()
        document = canvas.Canvas(stream, pagesize=letter)
        document.setFont('Helvetica-Bold', 14)
        document.drawString(54, 750, 'SOU Entry AccessHub access report')
        document.setFont('Helvetica', 10)
        y = 720
        for key, value in metrics.items():
            if isinstance(value, list):
                continue
            document.drawString(54, y, f'{key.replace("_", " ").title()}: {value}')
            y -= 18
        document.save()
        artifacts.append(('access-report.pdf', stream.getvalue(), 'application/pdf'))
    return artifacts


def generate_report(period, starts_at, ends_at, recipients, formats):
    metrics = metrics_for_window(starts_at, ends_at)
    report = AccessReport.objects.create(period=period, starts_at=starts_at, ends_at=ends_at, metrics=metrics)
    message = EmailMessage(
        f'{period.title()} SOU Entry AccessHub report',
        f'Report window: {starts_at.isoformat()} to {ends_at.isoformat()}',
        settings.DEFAULT_FROM_EMAIL,
        recipients,
    )
    for name, content, content_type in build_artifacts(metrics, formats):
        message.attach(name, content, content_type)
    if recipients:
        message.send(fail_silently=False)
    return report
