from django.test import TestCase
from django.urls import reverse
import time
from accounts.models import Branch, User


class StudentDashboardTests(TestCase):
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

    def test_token_requires_recent_live_verification(self):
        branch = Branch.objects.create(name='Token Branch', code='TOKEN')
        student = User.objects.create_user(email='token-student@example.com', password='StrongPassword123!', full_name='Token Student', enrollment_number='TOK-001', branch=branch)
        student.is_email_verified = True
        student.is_approved_by_admin = True
        student.save(update_fields=['is_email_verified', 'is_approved_by_admin'])
        self.client.force_login(student)
        endpoint = reverse('dashboard:issue_token')
        self.assertEqual(self.client.post(endpoint).status_code, 403)
        session = self.client.session
        session['live_face_verified_email'] = student.email
        session['live_face_verified_at'] = time.time()
        session.save()
        response = self.client.post(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['token'])
