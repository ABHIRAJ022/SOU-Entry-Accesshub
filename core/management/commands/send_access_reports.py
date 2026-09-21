from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.access_reports import generate_report
from core.models import AccessReportSchedule


class Command(BaseCommand):
    help = 'Generate and email configured daily, weekly, or monthly access reports.'

    def add_arguments(self, parser):
        parser.add_argument('--period', choices=['daily', 'weekly', 'monthly'])

    def handle(self, *args, **options):
        schedules = AccessReportSchedule.objects.filter(enabled=True)
        if options['period']:
            schedules = schedules.filter(period=options['period'])
        now = timezone.now()
        for schedule in schedules:
            if schedule.last_sent_at and schedule.last_sent_at.date() == now.date() and not options['period']:
                continue
            duration = {'daily': timedelta(days=1), 'weekly': timedelta(days=7), 'monthly': timedelta(days=30)}[schedule.period]
            starts_at = now - duration
            if not schedule.recipients:
                self.stderr.write(f'Skipping {schedule.period}: no recipients configured.')
                continue
            try:
                generate_report(schedule.period, starts_at, now, schedule.recipients, schedule.formats)
            except Exception as exc:
                raise CommandError(f'Could not send {schedule.period} report: {exc}') from exc
            schedule.last_sent_at = now
            schedule.save(update_fields=['last_sent_at'])
            self.stdout.write(self.style.SUCCESS(f'Sent {schedule.period} report.'))
