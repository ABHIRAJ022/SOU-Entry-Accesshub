from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import LocationHistory


class LocationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.student = User.objects.create_user(
            email='location-student@example.com', password='StrongPassword123!',
            full_name='Location Student', enrollment_number='LOC-001',
        )

    def test_location_is_opt_in(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('location_update'), {'latitude': 23, 'longitude': 72},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_update_rejects_out_of_range_coordinates(self):
        self.student.location_sharing_enabled = True
        self.student.save(update_fields=['location_sharing_enabled'])
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('location_update'), {'latitude': 91, 'longitude': 72},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_students_cannot_list_users(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('location_users')).status_code, 403)

    def test_cleanup_removes_only_expired_history(self):
        old = timezone.now() - timedelta(days=31)
        LocationHistory.objects.create(user=self.student, latitude=23, longitude=72, recorded_at=old)
        LocationHistory.objects.create(user=self.student, latitude=23, longitude=72, recorded_at=timezone.now())
        call_command('cleanup_location_history')
        self.assertEqual(LocationHistory.objects.filter(user=self.student).count(), 1)
