from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from .crypto import decrypt_vector, encrypt_vector
from .models import FaceProfile


class BiometricSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='biometric@example.com', password='StrongPassword123!',
            full_name='Biometric User', role=User.Role.ADMIN,
        )
        self.user.is_email_verified = True
        self.user.is_approved_by_super_admin = True
        self.user.save(update_fields=['is_email_verified', 'is_approved_by_super_admin'])
        self.client.force_login(self.user)

    def _session_capture(self):
        self.client.get(reverse('biometrics:enroll_page'), secure=True)
        return self.client.session['biometric_capture_id']

    def _payload(self, capture_id):
        return {'capture_mode': 'webcam', 'capture_id': capture_id, 'frames': [
            {'sequence': index, 'timestamp_ms': (index + 1) * 500, 'data': 'data:image/jpeg;base64,ZmFrZQ=='}
            for index in range(5)
        ]}

    def test_vectors_are_encrypted_at_rest(self):
        vector = [0.1, 0.2, -0.3]
        encrypted = encrypt_vector(vector)
        self.assertNotEqual(encrypted, ','.join(map(str, vector)))
        self.assertEqual(decrypt_vector(encrypted), vector)

    @patch('biometrics.views.has_liveness_variation', return_value=True)
    @patch('biometrics.views.analyze_frame', return_value=([0.1, 0.2, 0.3], {}, 100.0))
    @patch('biometrics.views.decode_webcam_frame', return_value=object())
    def test_enrollment_stores_encrypted_profile(self, decode, analyze, liveness):
        capture_id = self._session_capture()
        response = self.client.post(reverse('biometrics:enroll'), data=self._payload(capture_id), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        profile = FaceProfile.objects.get(user=self.user)
        self.assertNotIn('0.1,0.2,0.3', profile.encrypted_vector)
        self.assertEqual(decrypt_vector(profile.encrypted_vector), [0.1, 0.2, 0.3])

    def test_static_image_payload_is_rejected(self):
        capture_id = self._session_capture()
        payload = self._payload(capture_id)
        payload['capture_mode'] = 'upload'
        response = self.client.post(reverse('biometrics:enroll'), data=payload, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn('live webcam', response.json()['error'])

    def test_http_camera_request_is_rejected(self):
        capture_id = self._session_capture()
        response = self.client.post(reverse('biometrics:enroll'), data=self._payload(capture_id), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('HTTPS', response.json()['error'])

    def test_unauthenticated_api_is_rejected(self):
        self.client.logout()
        response = self.client.post(reverse('biometrics:enroll'), data={}, content_type='application/json', secure=True)
        self.assertIn(response.status_code, (302, 401, 403))

    def test_camera_permissions_policy_allows_same_origin_camera(self):
        response = self.client.get(reverse('biometrics:enroll_page'), secure=True)
        self.assertEqual(response['Permissions-Policy'], 'camera=(self), microphone=(), geolocation=()')
