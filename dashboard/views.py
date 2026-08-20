from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from accounts.models import User
from biometrics.views import has_recent_live_verification
from .models import CampusToken

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles: return JsonResponse({'error': 'Forbidden'}, status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

@role_required(User.Role.ADMIN, User.Role.SECURITY, User.Role.STUDENT)
def home(request):
    if request.user.role == User.Role.ADMIN: return admin_dashboard(request)
    if request.user.role == User.Role.SECURITY: return security_dashboard(request)
    return render(request, 'dashboard/student.html', {
        'student': request.user,
        'email_verified': request.user.is_email_verified,
        'approval_status': 'approved' if request.user.is_approved_by_admin else ('rejected' if not request.user.is_active else 'pending'),
    })

@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    students = User.objects.filter(role=User.Role.STUDENT)
    if not request.user.is_superuser:
        students = students.filter(branch=request.user.branch)
    staff_approvals = User.objects.none()
    if request.user.is_superuser:
        staff_approvals = User.objects.filter(role__in=(User.Role.ADMIN, User.Role.SECURITY), is_superuser=False)
    return render(request, 'dashboard/admin.html', {
        'students': students,
        'staff_approvals': staff_approvals,
        'is_super_admin': request.user.is_superuser,
        'branch': request.user.branch,
        'total_students': students.count(),
        'pending': students.filter(is_approved_by_admin=False, is_email_verified=True).count(),
        'active_staff': User.objects.filter(role=User.Role.SECURITY, is_active=True, is_approved_by_super_admin=True).count(),
    })

@role_required(User.Role.SECURITY)
def security_dashboard(request): return render(request, 'dashboard/security.html')

@require_POST
@role_required(User.Role.ADMIN)
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id); action = request.POST.get('action')
    if action not in {'approve', 'reject'}: return JsonResponse({'error': 'Invalid action'}, status=400)
    if user.role == User.Role.STUDENT:
        if not request.user.is_superuser and (request.user.role != User.Role.ADMIN or request.user.branch_id != user.branch_id):
            return JsonResponse({'error': 'You can only manage students in your assigned branch.'}, status=403)
        user.is_approved_by_admin = action == 'approve'
        user.is_active = action == 'approve'
        user.save(update_fields=['is_approved_by_admin', 'is_active'])
        return JsonResponse({'status': 'approved' if action == 'approve' else 'rejected'})
    if user.role in {User.Role.ADMIN, User.Role.SECURITY} and request.user.is_superuser:
        user.is_approved_by_super_admin = action == 'approve'
        user.is_active = action == 'approve'
        user.save(update_fields=['is_approved_by_super_admin', 'is_active'])
        return JsonResponse({'status': 'approved' if action == 'approve' else 'rejected'})
    return JsonResponse({'error': 'Only the main super administrator can manage staff accounts.'}, status=403)

@require_GET
@role_required(User.Role.SECURITY)
def student_lookup(request):
    query = request.GET.get('q', '').strip()[:32]
    users = User.objects.filter(role=User.Role.STUDENT).filter(Q(enrollment_number__icontains=query) | Q(full_name__icontains=query))[:10] if query else []
    return JsonResponse({'results': [{'name': user.full_name, 'enrollment_number': user.enrollment_number, 'email_verified': user.is_email_verified, 'approved': user.is_approved_by_admin, 'active': user.is_active} for user in users]})

@require_POST
@role_required(User.Role.STUDENT)
def issue_token(request):
    if not request.user.can_login or not has_recent_live_verification(request, request.user.email):
        return JsonResponse({'error': 'Complete a live face verification immediately before requesting a token.'}, status=403)
    token, raw_token = CampusToken.issue(request.user)
    return JsonResponse({'token': raw_token, 'generation': token.generation, 'expires_at': token.expires_at.isoformat()})

@require_POST
@role_required(User.Role.STUDENT)
def regenerate_token(request):
    return issue_token(request)
