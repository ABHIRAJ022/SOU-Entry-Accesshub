from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import OperationalError
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from .admin import AccountUserAdmin, AccountUserAdminForm
from .models import Branch, EmailOTP, User

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationContractTests(TestCase):
    def setUp(self):
        cache.clear()
        self.branch = Branch.objects.create(name='Central Branch', code='CENTRAL')
        self.user = User.objects.create_user(email='student@example.com', password='StrongPassword123!', full_name='Test Student', enrollment_number='STU-001', branch=self.branch)
        self.user.is_email_verified = True
        self.user.save(update_fields=['is_email_verified'])

    def test_student_requires_admin_approval(self):
        response = self.client.post(reverse('accounts:login'), {'role': User.Role.STUDENT, 'username': self.user.email, 'password': 'StrongPassword123!'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_student_can_login_after_approval(self):
        self.user.is_approved_by_admin = True
        self.user.save(update_fields=['is_approved_by_admin'])
        session = self.client.session
        session['live_face_verified_email'] = self.user.email
        session['live_face_verified_at'] = __import__('time').time()
        session.save()
        response = self.client.post(reverse('accounts:login'), {'role': User.Role.STUDENT, 'username': self.user.email, 'password': 'StrongPassword123!'})
        self.assertRedirects(response, reverse('dashboard:home'))

    def test_login_rejects_mismatched_role(self):
        self.user.is_approved_by_admin = True
        self.user.save(update_fields=['is_approved_by_admin'])
        response = self.client.post(reverse('accounts:login'), {'role': User.Role.SECURITY, 'username': self.user.email, 'password': 'StrongPassword123!'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'selected account type does not match')

    def test_https_localhost_origin_is_trusted_for_login(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:login'))
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(
            reverse('accounts:login'),
            {'role': User.Role.STUDENT, 'username': self.user.email, 'password': 'StrongPassword123!'},
            HTTP_ORIGIN='https://localhost:8000',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(CSRF_TRUSTED_ORIGINS=['https://*.vercel.app'], ALLOWED_HOSTS=['testserver', '.vercel.app'])
    def test_vercel_preview_origin_is_trusted_for_login(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:login'), HTTP_HOST='smart-entry-token-point-pts7pktuj.vercel.app', secure=True)
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(
            reverse('accounts:login'),
            {'role': User.Role.STUDENT, 'username': self.user.email, 'password': 'StrongPassword123!'},
            HTTP_HOST='smart-entry-token-point-pts7pktuj.vercel.app',
            HTTP_ORIGIN='https://smart-entry-token-point-pts7pktuj.vercel.app',
            HTTP_X_CSRFTOKEN=token,
            secure=True,
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_csrf_token_uses_recovery_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse('accounts:login'),
            {'username': self.user.email, 'password': 'StrongPassword123!', 'csrfmiddlewaretoken': 'stale-token'},
            HTTP_ORIGIN='https://localhost:8000',
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Reload secure form', status_code=403)

    @patch('accounts.forms.authenticate', side_effect=OperationalError)
    def test_login_handles_database_outage(self, authenticate_mock):
        response = self.client.post(
            reverse('accounts:login'),
            {'role': User.Role.STUDENT, 'username': self.user.email, 'password': 'StrongPassword123!'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign-in is temporarily unavailable')
        authenticate_mock.assert_called_once()

    def test_form_pages_issue_csrf_cookie(self):
        for url_name in ('accounts:login', 'accounts:register', 'accounts:verify_otp'):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)
            self.assertIn(settings.CSRF_COOKIE_NAME, self.client.cookies)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('accounts:logout')), reverse('accounts:login'))

    def test_registration_uses_local_email_backend(self):
        response = self.client.post(reverse('accounts:register'), {
            'role': User.Role.STUDENT,
            'branch': self.branch.pk,
            'email': 'newstudent@example.com',
            'full_name': 'New Student',
            'enrollment_number': 'STU-002',
            'phone_number': '9601270941',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })
        self.assertRedirects(response, reverse('accounts:verify_otp'))
        self.assertTrue(User.objects.filter(email='newstudent@example.com').exists())

    def test_pending_user_can_resend_otp(self):
        user = User.objects.create_user(email='pending@example.com', password='StrongPassword123!', full_name='Pending Student', enrollment_number='STU-004')
        session = self.client.session
        session['pending_email'] = user.email
        session.save()
        response = self.client.post(reverse('accounts:resend_otp'))
        self.assertRedirects(response, reverse('accounts:verify_otp'))
        self.assertEqual(EmailOTP.objects.filter(user=user).count(), 1)

    def test_admin_delete_handles_missing_tokenscan_table(self):
        superuser = User.objects.create_superuser(email='admin-delete@example.com', password='StrongPassword123!', full_name='Admin Delete')
        user = User.objects.create_user(email='delete-user@example.com', password='StrongPassword123!', full_name='Delete User', enrollment_number='STU-DELETE', branch=self.branch)
        admin_site = admin.site
        admin_obj = AccountUserAdmin(User, admin_site)
        request = RequestFactory().get('/admin/accounts/user/')
        request.user = superuser
        with patch('accounts.admin._token_scan_table_available', return_value=False):
            self.assertEqual(admin_obj.get_deleted_objects([user], request)[1]['accounts.User'], 1)
            admin_obj.delete_queryset(request, User.objects.filter(pk=user.pk))
            self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_valid_otp_redirects_to_login(self):
        user = User.objects.create_user(email='verify@example.com', password='StrongPassword123!', full_name='Verify Student', enrollment_number='STU-005', branch=self.branch)
        from django.contrib.auth.hashers import make_password
        EmailOTP.objects.create(user=user, code_hash=make_password('371090'))
        session = self.client.session
        session['pending_email'] = user.email
        session.save()
        response = self.client.post(reverse('accounts:verify_otp'), {'code': '371090'})
        self.assertRedirects(response, reverse('accounts:login'))
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='127.0.0.1', EMAIL_PORT=1, EMAIL_TIMEOUT=1,
    )
    def test_registration_handles_unavailable_smtp(self):
        response = self.client.post(reverse('accounts:register'), {
            'role': User.Role.STUDENT,
            'branch': self.branch.pk,
            'email': 'smtp-failure@example.com',
            'full_name': 'SMTP Failure',
            'enrollment_number': 'STU-003',
            'phone_number': '9601270941',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'could not send the verification email')
        self.assertFalse(User.objects.filter(email='smtp-failure@example.com').exists())

    def test_registration_persists_staff_roles(self):
        for role, email, enrollment in ((User.Role.ADMIN, 'admin@example.com', ''), (User.Role.SECURITY, 'security@example.com', '')):
            response = self.client.post(reverse('accounts:register'), {
                'role': role, 'email': email, 'full_name': role.title(),
                'enrollment_number': enrollment, 'phone_number': '9601270941',
                'password1': 'StrongPassword123!', 'password2': 'StrongPassword123!',
            })
            self.assertRedirects(response, reverse('accounts:verify_otp'))
            user = User.objects.get(email=email)
            self.assertEqual(user.role, role)
            self.assertFalse(user.is_approved_by_super_admin)

    def test_staff_registration_form_hides_student_only_fields(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertContains(response, 'data-student-only-field="branch"')
        self.assertContains(response, 'register.js')

    def test_staff_cannot_login_before_super_admin_approval(self):
        staff = User.objects.create_user(email='staff-pending@example.com', password='StrongPassword123!', full_name='Pending Staff', role=User.Role.SECURITY)
        staff.is_email_verified = True
        staff.save(update_fields=['is_email_verified'])
        response = self.client.post(reverse('accounts:login'), {'role': User.Role.SECURITY, 'username': staff.email, 'password': 'StrongPassword123!'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify your email and await admin approval')

    def test_authenticated_user_can_view_read_only_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.email)

        response = self.client.post(reverse('accounts:profile'), {
            'full_name': 'Updated Student',
            'phone_number': '9876543210',
        })
        self.assertEqual(response.status_code, 405)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Test Student')
        self.assertEqual(self.user.phone_number, '')
        self.assertFalse(self.user.profile_photo)
        profile = self.client.get(reverse('accounts:profile'))
        self.assertContains(profile, 'managed by campus administration')
        self.assertNotContains(profile, 'Save profile')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("accounts:profile")}')

    def test_admin_form_can_upload_profile_photo(self):
        image = BytesIO()
        Image.new('RGB', (40, 40), 'navy').save(image, format='PNG')
        form = AccountUserAdminForm(
            data={'email': self.user.email, 'password': self.user.password, 'date_joined': self.user.date_joined.strftime('%Y-%m-%d %H:%M:%S'), 'full_name': self.user.full_name, 'phone_number': '', 'role': User.Role.STUDENT, 'branch': self.branch.pk},
            files={'profile_photo': SimpleUploadedFile('profile.png', image.getvalue(), content_type='image/png')},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo.startswith(b'\x89PNG'))

class HealthContractTests(TestCase):
    def test_health_endpoint_reports_operational_database(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'operational')
        self.assertNotIn('database', response.json())
