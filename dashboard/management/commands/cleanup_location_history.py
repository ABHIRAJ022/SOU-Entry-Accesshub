from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import LocationHistory


class Command(BaseCommand):
    help = 'Remove location history older than the configured retention period.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=getattr(settings, 'LOCATION_HISTORY_RETENTION_DAYS', 30))
        deleted, _ = LocationHistory.objects.filter(recorded_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} location history records.'))
