import base64
import time
from io import BytesIO
from django.test import TestCase, override_settings
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from PIL import Image
from accounts.models import Branch, User
from biometrics.models import IdentityVerification
from .models import CampusLocation, CampusToken, GuestTokenRequest, TokenNotification
from .token_utils import signed_payload
from .token_utils import signed_payload, verify_signed_payload
from .notifications import send_token_created


class StudentDashboardTests(TestCase):
    def setUp(self):
        cache.clear()

    def _image(self):
        output = BytesIO()
        Image.new('RGB', (320, 240), (128, 128, 128)).save(output, format='JPEG')
        return f"data:image/jpeg;base64,{base64.b64encode(output.getvalue()).decode()}"

    def _token_payload(self, duration=30):
        return {'duration_minutes': duration, 'capture_mode': 'webcam', 'captured_at': time.time(), 'image': self._image()}

    def _set_identity_verification(self, user):
        verification = IdentityVerification.objects.create(user=user, audit_snapshot=b'audit', snapshot_size=5, verification_method='pin', expires_at=timezone.now() + timedelta(minutes=5))
        session = self.client.session
        session['identity_verification_id'] = verification.pk
        session['identity_verified_at'] = timezone.now().timestamp()
        session.save()

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
        endpoint = reverse('dashboard:issue_token')
        response = self.client.post(endpoint, self._token_payload(120), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['token'])
        self.assertEqual(response.json()['expires_at'][:16], (timezone.now() + timedelta(minutes=120)).isoformat()[:16])
        self.assertEqual(verify_signed_payload(response.json()['qr_payload'])['token_id'], response.json()['token_id'])

    def test_guest_can_submit_temporary_token_request(self):
        response = self.client.post(reverse('accounts:guest_request'), {
            'name': 'Parent Visitor', 'gender': 'PREFER_NOT_TO_SAY', 'email': 'parent@example.com', 'mobile': '+91 9876543210',
            'purpose': 'Attend the student orientation', 'duration_minutes': 120, 'live_photo': self._image(),
        })
        self.assertRedirects(response, reverse('accounts:login'))
        guest = GuestTokenRequest.objects.get()
        self.assertEqual(guest.status, GuestTokenRequest.Status.PENDING)
        self.assertFalse(CampusToken.objects.exists())

    def test_security_staff_can_approve_guest_request_once(self):
        guest = GuestTokenRequest.objects.create(name='Guest Parent', gender='FEMALE', email='', mobile='9876543210', purpose='Visit student', duration_minutes=60, live_photo=b'guest-photo')
        security = User.objects.create_user(email='guest-security@example.com', password='StrongPassword123!', full_name='Gate Security', role=User.Role.SECURITY)
        self.client.force_login(security)
        endpoint = reverse('dashboard:approve_guest_request', args=[guest.pk])
        response = self.client.post(endpoint)
        self.assertRedirects(response, reverse('dashboard:guest_request_detail', args=[guest.pk]))
        guest.refresh_from_db()
        self.assertEqual(guest.status, GuestTokenRequest.Status.APPROVED)
        self.assertEqual(guest.approved_by, security)
        self.assertEqual(CampusToken.objects.filter(guest_request=guest).count(), 1)
        self.assertEqual(self.client.post(endpoint).status_code, 200)
        self.assertEqual(CampusToken.objects.filter(guest_request=guest).count(), 1)

    def test_guest_cannot_request_second_token_while_first_is_active(self):
        guest = GuestTokenRequest.objects.create(name='Active Guest', gender='MALE', email='', mobile='9876543210', purpose='Visit student', duration_minutes=60, live_photo=b'guest-photo', status=GuestTokenRequest.Status.APPROVED)
        CampusToken.issue_for_guest(guest)
        response = self.client.post(reverse('accounts:guest_request'), {
            'name': 'Active Guest', 'gender': 'MALE', 'mobile': '9876543210',
            'purpose': 'Visit again', 'duration_minutes': 30, 'live_photo': self._image(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('An active token already exists', response.content.decode())

    def test_guest_replacement_requires_main_admin_approval(self):
        old_guest = GuestTokenRequest.objects.create(name='Returning Guest', gender='FEMALE', email='', mobile='9988776655', purpose='First visit', duration_minutes=30, live_photo=b'guest-photo', status=GuestTokenRequest.Status.APPROVED)
        token, _ = CampusToken.issue_for_guest(old_guest)
        token.expires_at = timezone.now() - timedelta(minutes=1)
        token.save(update_fields=['expires_at'])
        response = self.client.post(reverse('accounts:guest_request'), {
            'name': 'Returning Guest', 'gender': 'FEMALE', 'mobile': '9988776655',
            'purpose': 'Second visit', 'duration_minutes': 30, 'live_photo': self._image(),
        })
        self.assertRedirects(response, reverse('accounts:login'))
        replacement = GuestTokenRequest.objects.exclude(pk=old_guest.pk).get()
        self.assertEqual(replacement.status, GuestTokenRequest.Status.MAIN_ADMIN_REQUIRED)

    def test_main_admin_can_cancel_live_guest_token(self):
        guest = GuestTokenRequest.objects.create(name='Cancellable Guest', gender='MALE', email='', mobile='8877665544', purpose='Visit student', duration_minutes=60, live_photo=b'guest-photo', status=GuestTokenRequest.Status.APPROVED)
        token, _ = CampusToken.issue_for_guest(guest)
        admin = User.objects.create_superuser(email='main-admin-cancel@example.com', password='StrongPassword123!', full_name='Main Admin')
        self.client.force_login(admin)
        response = self.client.post(reverse('dashboard:cancel_token', args=[token.public_id]))
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertIsNotNone(token.revoked_at)
        guest.refresh_from_db()
        self.assertEqual(guest.status, GuestTokenRequest.Status.CANCELLED)

    def test_guest_detail_loads_cancel_handler_for_main_admin(self):
        guest = GuestTokenRequest.objects.create(name='Detail Guest', gender='FEMALE', email='', mobile='7766554433', purpose='Visit student', duration_minutes=60, live_photo=b'guest-photo', status=GuestTokenRequest.Status.APPROVED)
        token, _ = CampusToken.issue_for_guest(guest)
        admin = User.objects.create_superuser(email='detail-admin@example.com', password='StrongPassword123!', full_name='Detail Admin')
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:guest_request_detail', args=[guest.pk]))
        self.assertContains(response, 'data-cancel-token')
        self.assertContains(response, 'js/dashboard.js')
        self.assertContains(response, 'csrfmiddlewaretoken')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_token_pdf_is_emailed_to_student(self):
        student = User.objects.create_user(email='pdf-student@example.com', password='StrongPassword123!', full_name='PDF Student', enrollment_number='PDF-001')
        token, _ = CampusToken.issue(student, 30)
        send_token_created(token)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [student.email])
        self.assertEqual(mail.outbox[0].attachments[0][0], f'campus-pass-{token.public_id}.pdf')
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_guest_token_pdf_is_emailed_when_email_is_provided(self):
        guest = GuestTokenRequest.objects.create(name='Email Guest', gender='MALE', email='guest-pdf@example.com', mobile='9876543210', purpose='Visit student', duration_minutes=60, live_photo=b'guest-photo')
        token, _ = CampusToken.issue_for_guest(guest)
        send_token_created(token)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [guest.email])
        self.assertTrue(mail.outbox[0].attachments[0][0].endswith('.pdf'))

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
        self._set_identity_verification(student)
        endpoint = reverse('dashboard:issue_token')
        first = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
        self.assertEqual(second.status_code, 409)
        self.assertIn('active token', second.json()['error'])
        student.campus_tokens.update(expires_at=timezone.now() - timedelta(seconds=1))
        third = self.client.post(endpoint, self._token_payload(120), content_type='application/json', secure=True)
        self.assertEqual(third.status_code, 200)

    def test_student_can_generate_at_most_three_tokens_per_day(self):
        branch = Branch.objects.create(name='Daily Limit Branch', code='DAILY')
        student = User.objects.create_user(email='daily-limit@example.com', password='StrongPassword123!', full_name='Daily Limit Student', enrollment_number='DAILY-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        self._set_identity_verification(student)
        endpoint = reverse('dashboard:issue_token')

        for _ in range(3):
            response = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
            self.assertEqual(response.status_code, 200)
            student.campus_tokens.update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.client.post(endpoint, self._token_payload(), content_type='application/json', secure=True)
        self.assertEqual(response.status_code, 409)
        self.assertIn('maximum of 3 tokens per day', response.json()['error'])

    def test_one_hour_duration_is_supported(self):
        branch = Branch.objects.create(name='One Hour Branch', code='ONE-HOUR')
        student = User.objects.create_user(email='one-hour@example.com', password='StrongPassword123!', full_name='One Hour Student', enrollment_number='ONE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        self._set_identity_verification(student)
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

    def test_token_status_sends_two_minute_expiry_notice_once(self):
        branch = Branch.objects.create(name='Notice Branch', code='NOTICE')
        student = User.objects.create_user(email='notice@example.com', password='StrongPassword123!', full_name='Notice Student', enrollment_number='NOTICE-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        token, _ = CampusToken.issue(student, 30)
        token.expires_at = timezone.now() + timedelta(seconds=90)
        token.save(update_fields=['expires_at'])
        self.client.force_login(student)
        endpoint = reverse('dashboard:token_status', args=[token.public_id])
        self.assertEqual(self.client.get(endpoint).status_code, 200)
        self.assertEqual(TokenNotification.objects.filter(token=token, kind='2m').count(), 1)
        self.client.get(endpoint)
        self.assertEqual(TokenNotification.objects.filter(token=token, kind='2m').count(), 1)


class AdminTokenManagementTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(name='Admin Token Branch', code='ADMIN-TOKEN')
        self.admin = User.objects.create_user(email='token-admin@example.com', password='StrongPassword123!', full_name='Token Admin', role=User.Role.ADMIN, branch=self.branch)
        self.student = User.objects.create_user(email='managed-student@example.com', password='StrongPassword123!', full_name='Managed Student', enrollment_number='MANAGED-001', branch=self.branch)
        self.other_branch = Branch.objects.create(name='Other Token Branch', code='OTHER-TOKEN')
        self.other_student = User.objects.create_user(email='other-managed@example.com', password='StrongPassword123!', full_name='Other Managed', enrollment_number='OTHER-001', branch=self.other_branch)
        self.client.force_login(self.admin)

    def test_management_page_lists_live_and_expired_tokens(self):
        expired, _ = CampusToken.issue(self.student, 30)
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=['expires_at'])
        live, _ = CampusToken.issue(self.student, 30)
        response = self.client.get(reverse('dashboard:token_management'))
        self.assertContains(response, str(live.public_id))
        self.assertContains(response, str(expired.public_id))

    def test_branch_admin_cannot_access_other_student_history_or_cancel_token(self):
        token, _ = CampusToken.issue(self.other_student, 30)
        self.assertEqual(self.client.get(reverse('dashboard:token_history', args=[self.other_student.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse('dashboard:cancel_token', args=[token.public_id])).status_code, 404)

    def test_admin_can_cancel_live_token_without_deleting_history(self):
        token, _ = CampusToken.issue(self.student, 30)
        response = self.client.post(reverse('dashboard:cancel_token', args=[token.public_id]))
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertIsNotNone(token.revoked_at)
        self.assertContains(self.client.get(reverse('dashboard:token_history', args=[self.student.id])), str(token.public_id))
