import base64
import time
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Branch, User
from dashboard.models import TokenAudit
from .models import IdentityVerification


@override_settings(RATELIMIT_ENABLE=False)
class IdentityVerificationTests(TestCase):
    def setUp(self):
        branch = Branch.objects.create(name='North', code='NORTH')
        self.user = User.objects.create_user(email='identity-student@example.com', password='StrongPassword123!', full_name='Student', enrollment_number='ID-001', branch=branch)
        self.user.is_email_verified = True
        self.user.is_approved_by_admin = True
        self.user.set_security_pin('123456')
        self.user.save(update_fields=['is_email_verified', 'is_approved_by_admin', 'security_pin_hash'])
        self.client.force_login(self.user)

    def _image(self):
        output = BytesIO()
        Image.new('RGB', (320, 240), (128, 128, 128)).save(output, format='JPEG')
        return f"data:image/jpeg;base64,{base64.b64encode(output.getvalue()).decode()}"

    def _payload(self):
        return {'capture_mode': 'webcam', 'capture_id': self.client.session['identity_capture_id'], 'captured_at': time.time(), 'image': self._image(), 'pin': '123456'}

    def _start(self):
        self.client.get(reverse('biometrics:verify_page'), secure=True)

    def test_snapshot_and_pin_create_temporary_verification(self):
        self._start()
        response = self.client.post(reverse('biometrics:verify_identity'), self._payload(), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        verification = IdentityVerification.objects.get(user=self.user)
        self.assertLessEqual(verification.snapshot_size, 200 * 1024)
        self.assertTrue(self.client.session['identity_verified'])

    def test_static_upload_is_rejected(self):
        self._start()
        payload = self._payload()
        payload['capture_mode'] = 'upload'
        response = self.client.post(reverse('biometrics:verify_identity'), payload, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn('live webcam', response.json()['error'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('biometrics.views.secrets.randbelow', return_value=1234)
    def test_emergency_otp_can_verify(self, randbelow):
        self._start()
        self.client.post(reverse('biometrics:request_emergency_otp'), secure=True)
        payload = self._payload()
        payload.pop('pin')
        payload['otp'] = '1234'
        response = self.client.post(reverse('biometrics:verify_identity'), payload, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)

    def test_identity_verification_is_consumed_by_token_generation(self):
        self._start()
        self.client.post(reverse('biometrics:verify_identity'), self._payload(), content_type='application/json', secure=True)
        payload = {'duration_minutes': 30, 'capture_mode': 'webcam', 'captured_at': time.time(), 'image': self._image()}
        response = self.client.post(reverse('dashboard:issue_token'), payload, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TokenAudit.objects.count(), 1)
        self.assertEqual(TokenAudit.objects.get().verification_method, 'webcam')