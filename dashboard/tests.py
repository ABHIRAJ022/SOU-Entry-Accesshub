import base64
import time
from io import BytesIO
from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from PIL import Image
from accounts.models import Branch, User
from biometrics.models import IdentityVerification
from .models import CampusLocation, CampusToken
from .token_utils import signed_payload
from .token_utils import signed_payload, verify_signed_payload


class StudentDashboardTests(TestCase):
    def setUp(self):
        cache.clear()

    def _image(self):
        output = BytesIO()
        Image.new('RGB', (320, 240), (128, 128, 128)).save(output, format='JPEG')
        return f"data:image/jpeg;base64,{base64.b64encode(output.getvalue()).decode()}"

    def _token_payload(self, duration=30):
        return {'duration_minutes': duration, 'capture_mode': 'webcam', 'captured_at': time.time(), 'image': self._image()}

    def test_approved_student_sees_approved_status(self):
        user = User.objects.create_user(
            email='approved@example.com', password='StrongPassword123!',
            full_name='Approved Student', enrollment_number='APP-001',
        )
        user.is_email_verified = True
        user.is_approved_by_admin = True
        user.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Approved')
        self.assertNotContains(response, 'Pending Admin Approval')

    def test_pending_student_sees_pending_status(self):
        user = User.objects.create_user(
            email='pending-dashboard@example.com', password='StrongPassword123!',
            full_name='Pending Student', enrollment_number='PEN-001',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'Pending Admin Approval')

    def test_staff_roles_route_to_their_dashboards(self):
        admin = User.objects.create_user(email='admin-route@example.com', password='StrongPassword123!', full_name='Admin', role=User.Role.ADMIN)
        self.client.force_login(admin)
        self.assertContains(self.client.get(reverse('dashboard:home')), 'Campus overview')
        security = User.objects.create_user(email='security-route@example.com', password='StrongPassword123!', full_name='Security', role=User.Role.SECURITY)
        self.client.force_login(security)
        self.assertContains(self.client.get(reverse('dashboard:home')), 'Campus verification')

    def test_branch_admin_can_only_approve_own_branch_students(self):
        first = Branch.objects.create(name='North Branch', code='NORTH')
        second = Branch.objects.create(name='South Branch', code='SOUTH')
        branch_admin = User.objects.create_user(email='branch-admin@example.com', password='StrongPassword123!', full_name='Branch Admin', role=User.Role.ADMIN, branch=first)
        branch_admin.is_email_verified = True
        branch_admin.is_approved_by_super_admin = True
        branch_admin.save(update_fields=['is_email_verified', 'is_approved_by_super_admin'])
        own_student = User.objects.create_user(email='own-student@example.com', password='StrongPassword123!', full_name='Own Student', enrollment_number='OWN-001', branch=first)
        other_student = User.objects.create_user(email='other-student@example.com', password='StrongPassword123!', full_name='Other Student', enrollment_number='OTH-001', branch=second)
        self.client.force_login(branch_admin)
        url = reverse('dashboard:approve_user', args=[own_student.id])
        self.assertEqual(self.client.post(url, {'action': 'approve'}).status_code, 200)
        self.assertEqual(self.client.post(reverse('dashboard:approve_user', args=[other_student.id]), {'action': 'approve'}).status_code, 403)

    def test_approved_student_can_be_revoked(self):
        branch = Branch.objects.create(name='Revoke Branch', code='REVOKE')
        admin = User.objects.create_user(email='revoke-admin@example.com', password='StrongPassword123!', full_name='Revoke Admin', role=User.Role.ADMIN, branch=branch)
        admin.is_email_verified = True
        admin.is_approved_by_super_admin = True
        admin.save(update_fields=['is_email_verified', 'is_approved_by_super_admin'])
        student = User.objects.create_user(email='revoke-student@example.com', password='StrongPassword123!', full_name='Revoke Student', enrollment_number='REV-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(admin)
        response = self.client.post(reverse('dashboard:approve_user', args=[student.id]), {'action': 'revoke'})
        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.is_approved_by_admin)
        self.assertFalse(student.is_active)

    def test_approved_student_can_generate_duration_token_after_identity_verification(self):
        branch = Branch.objects.create(name='Token Branch', code='TOKEN')
        student = User.objects.create_user(email='token-student@example.com', password='StrongPassword123!', full_name='Token Student', enrollment_number='TOK-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        verification = IdentityVerification.objects.create(user=student, audit_snapshot=b'audit', snapshot_size=5, verification_method='pin', expires_at=timezone.now() + timedelta(minutes=5))
        session = self.client.session
        session['identity_verified'] = True
        session['identity_verification_id'] = verification.pk
        session['identity_verified_at'] = timezone.now().timestamp()
        session.save()
        endpoint = reverse('dashboard:issue_token')
        response = self.client.post(endpoint, self._token_payload(120), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['token'])
        self.assertEqual(response.json()['expires_at'][:16], (timezone.now() + timedelta(minutes=120)).isoformat()[:16])
        self.assertEqual(verify_signed_payload(response.json()['qr_payload'])['token_id'], response.json()['token_id'])

    def test_token_requires_live_photo(self):
        branch = Branch.objects.create(name='Gate Branch', code='GATE')
        student = User.objects.create_user(email='gate-student@example.com', password='StrongPassword123!', full_name='Gate Student', enrollment_number='GATE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        response = self.client.post(reverse('dashboard:issue_token'), {'duration_minutes': 30}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn('webcam', response.json()['error'])

    def test_active_token_blocks_second_token_until_expiry(self):
        branch = Branch.objects.create(name='Single Token Branch', code='SINGLE')
        student = User.objects.create_user(email='single-token@example.com', password='StrongPassword123!', full_name='Single Token Student', enrollment_number='SINGLE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        endpoint = reverse('dashboard:issue_token')
        first = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
        self.assertEqual(second.status_code, 409)
        self.assertIn('active token', second.json()['error'])
        student.campus_tokens.update(expires_at=timezone.now() - timedelta(seconds=1))
        third = self.client.post(endpoint, self._token_payload(120), content_type='application/json', secure=True)
        self.assertEqual(third.status_code, 200)

    def test_one_hour_duration_is_supported(self):
        branch = Branch.objects.create(name='One Hour Branch', code='ONE-HOUR')
        student = User.objects.create_user(email='one-hour@example.com', password='StrongPassword123!', full_name='One Hour Student', enrollment_number='ONE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        response = self.client.post(reverse('dashboard:issue_token'), self._token_payload(60), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['generation'], 1)

    def test_dashboard_shows_active_token_and_history_for_owner(self):
        branch = Branch.objects.create(name='History Branch', code='HISTORY')
        student = User.objects.create_user(email='history@example.com', password='StrongPassword123!', full_name='History Student', enrollment_number='HISTORY-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        token, _ = CampusToken.issue(student, 30)
        self.client.force_login(student)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, str(token.public_id))
        self.assertContains(response, 'ACTIVE')

    def test_dashboard_shows_latest_expired_token_inside_token_card(self):
        branch = Branch.objects.create(name='Expired Branch', code='EXPIRED')
        student = User.objects.create_user(email='expired-visible@example.com', password='StrongPassword123!', full_name='Expired Visible', enrollment_number='EXPIRED-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        token, _ = CampusToken.issue(student, 30)
        token.expires_at = timezone.now() - timedelta(minutes=1)
        token.save(update_fields=['expires_at'])
        self.client.force_login(student)
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, str(token.public_id))
        self.assertContains(response, 'EXPIRED')
        self.assertContains(response, 'Latest token')

    def test_active_token_is_visible_after_logout_and_login(self):
        branch = Branch.objects.create(name='Persistent Branch', code='PERSIST')
        student = User.objects.create_user(email='persistent@example.com', password='StrongPassword123!', full_name='Persistent Student', enrollment_number='PERSIST-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        token, _ = CampusToken.issue(student, 30)
        self.client.force_login(student)
        self.client.post(reverse('accounts:logout'))
        login_response = self.client.post(reverse('accounts:login'), {'role': User.Role.STUDENT, 'username': student.email, 'password': 'StrongPassword123!'})
        self.assertRedirects(login_response, reverse('dashboard:home'))
        dashboard_response = self.client.get(reverse('dashboard:home'))
        self.assertContains(dashboard_response, str(token.public_id))
        self.assertContains(dashboard_response, 'Active token')

    def test_security_validation_is_single_use(self):
        branch = Branch.objects.create(name='Gate Branch', code='GATE-TEST')
        student = User.objects.create_user(email='gate-student@example.com', password='StrongPassword123!', full_name='Gate Student', enrollment_number='GATE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        security = User.objects.create_user(email='guard@example.com', password='StrongPassword123!', full_name='Guard', role=User.Role.SECURITY)
        security.is_email_verified = True
        security.is_approved_by_super_admin = True
        security.save(update_fields=['is_email_verified', 'is_approved_by_super_admin'])
        token, _ = CampusToken.issue(student, 30)
        self.client.force_login(security)
        payload = {'qr_payload': signed_payload(token)}
        first = self.client.post(reverse('validate_token'), payload, content_type='application/json', secure=True)
        second = self.client.post(reverse('validate_token'), payload, content_type='application/json', secure=True)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['valid'])
        self.assertEqual(second.status_code, 409)

    def test_students_cannot_create_campus_locations(self):
        student = User.objects.create_user(email='map-student@example.com', password='StrongPassword123!', full_name='Map Student', enrollment_number='MAP-001')
        self.client.force_login(student)
        response = self.client.post('/api/locations/create/', {'name': 'Nope'}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 403)

    def test_admin_location_coordinates_are_validated(self):
        admin = User.objects.create_user(email='map-admin@example.com', password='StrongPassword123!', full_name='Map Admin', role=User.Role.ADMIN)
        admin.is_email_verified = True
        admin.is_approved_by_super_admin = True
        admin.save(update_fields=['is_email_verified', 'is_approved_by_super_admin'])
        self.client.force_login(admin)
        response = self.client.post('/api/locations/create/', {'name': 'Invalid', 'category': CampusLocation.Category.LIBRARY, 'latitude': 100, 'longitude': 10}, content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 400)

    def test_token_pdf_is_owner_protected_and_is_pdf(self):
        branch = Branch.objects.create(name='PDF Branch', code='PDF')
        student = User.objects.create_user(email='pdf-student@example.com', password='StrongPassword123!', full_name='PDF Student', enrollment_number='PDF-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        verification = IdentityVerification.objects.create(user=student, audit_snapshot=b'audit', snapshot_size=5, verification_method='pin', expires_at=timezone.now() + timedelta(minutes=5))
        session = self.client.session
        session['identity_verification_id'] = verification.pk
        session['identity_verified_at'] = timezone.now().timestamp()
        session.save()
        token = self.client.post(reverse('dashboard:issue_token'), self._token_payload(), content_type='application/json', secure=True).json()
        response = self.client.get(token['pdf_url'], secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
