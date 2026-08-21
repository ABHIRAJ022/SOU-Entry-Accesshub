import logging
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method == 'GET' and response.get('Content-Type', '').startswith('text/html'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
        response.setdefault('Permissions-Policy', 'camera=(self), microphone=(), geolocation=()')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response


class AuditLoggingMiddleware:
    AUDITED_PATHS = (
        '/accounts/login/', '/accounts/register/', '/accounts/verify-otp/',
        '/dashboard/tokens/generate/', '/dashboard/tokens/regenerate/',
        '/dashboard/users/', '/api/face/', '/api/verify-identity/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.AUDITED_PATHS) and request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            from .models import AuditLog
            event, action = self._event(request.path)
            user = request.user if getattr(request.user, 'is_authenticated', False) else None
            try:
                AuditLog.objects.create(
                    event=event, action=action, status=str(response.status_code), user=user,
                    ip_address=self._ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],
                    path=request.path, metadata={'method': request.method},
                )
            except (OperationalError, ProgrammingError):
                logger.exception('Audit log write skipped because the database schema is unavailable.')
        return response

    @staticmethod
    def _event(path):
        if '/login/' in path or '/register/' in path or '/verify-otp/' in path:
            return 'AUTHENTICATION', 'account_authentication'
        if '/tokens/' in path:
            return 'TOKEN_CREATED', 'token_operation'
        if '/users/' in path:
            return 'ADMIN_DECISION', 'admin_decision'
        return 'FACE_VERIFICATION', 'face_verification'

    @staticmethod
    def _ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        return forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR')
