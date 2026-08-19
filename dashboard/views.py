from functools import wraps
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST
from accounts.models import User

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
    return render(request, 'dashboard/student.html')

@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    students = User.objects.filter(role=User.Role.STUDENT)
    return render(request, 'dashboard/admin.html', {'students': students, 'total_students': students.count(), 'pending': students.filter(is_approved_by_admin=False, is_email_verified=True).count(), 'active_staff': User.objects.filter(role=User.Role.SECURITY, is_active=True).count()})

@role_required(User.Role.SECURITY)
def security_dashboard(request): return render(request, 'dashboard/security.html')

@require_POST
@role_required(User.Role.ADMIN)
def approve_user(request, user_id):
    user = get_object_or_404(User, id=user_id, role=User.Role.STUDENT); action = request.POST.get('action')
    if action not in {'approve', 'reject'}: return JsonResponse({'error': 'Invalid action'}, status=400)
    user.is_approved_by_admin = action == 'approve'; user.is_active = action == 'approve'; user.save(update_fields=['is_approved_by_admin', 'is_active'])
    return JsonResponse({'status': 'approved' if action == 'approve' else 'rejected'})

@require_GET
@role_required(User.Role.SECURITY)
def student_lookup(request):
    query = request.GET.get('q', '').strip()[:32]
    users = User.objects.filter(role=User.Role.STUDENT).filter(Q(enrollment_number__icontains=query) | Q(full_name__icontains=query))[:10] if query else []
    return JsonResponse({'results': [{'name': user.full_name, 'enrollment_number': user.enrollment_number, 'email_verified': user.is_email_verified, 'approved': user.is_approved_by_admin, 'active': user.is_active} for user in users]})
