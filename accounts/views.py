import base64
import logging
import secrets
from io import BytesIO
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from smtplib import SMTPException
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from PIL import Image
from .forms import GuestTokenRequestForm, OTPForm, RegistrationForm, SecureLoginForm
from .models import EmailOTP, User
from dashboard.models import GuestTokenRequest
from biometrics.snapshots import SnapshotError, process_webcam_snapshot
from django.contrib.auth.hashers import check_password, make_password

logger = logging.getLogger(__name__)

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard:home')
    form = SecureLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user()); return redirect('dashboard:home')
    return render(request, 'accounts/login.html', {'form': form})


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@ensure_csrf_cookie
def guest_request(request):
    form = GuestTokenRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            live_photo = process_webcam_snapshot({'capture_mode': 'webcam', 'image': form.cleaned_data['live_photo']})
        except SnapshotError as exc:
            form.add_error('live_photo', str(exc))
        else:
            data = form.cleaned_data.copy()
            data['live_photo'] = live_photo
            active_request = GuestTokenRequest.objects.filter(
                mobile=data['mobile'],
                status=GuestTokenRequest.Status.APPROVED,
                token__revoked_at__isnull=True,
                token__expires_at__gt=__import__('django.utils.timezone', fromlist=['now']).now(),
            ).exists()
            previous_request = GuestTokenRequest.objects.filter(mobile=data['mobile']).exists()
            data['status'] = GuestTokenRequest.Status.MAIN_ADMIN_REQUIRED if previous_request else GuestTokenRequest.Status.PENDING
            if active_request:
                form.add_error('mobile', 'An active token already exists for this mobile number. Wait until it expires before requesting another.')
            else:
                GuestTokenRequest.objects.create(**data)
                messages.success(request, 'Your temporary access request was submitted for security review.')
                return redirect('accounts:login')
    return render(request, 'accounts/guest_request.html', {'form': form})

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@transaction.atomic
@ensure_csrf_cookie
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        try:
            send_otp(user)
        except (OSError, SMTPException) as exc:
            logger.exception('OTP email delivery failed for %s: %s', user.email, exc)
            user.delete()
            form.add_error(None, 'We could not send the verification email. Please try again in a minute. If this continues, contact support.')
        else:
            request.session['pending_email'] = user.email
            if 'console.EmailBackend' in settings.EMAIL_BACKEND:
                messages.success(request, 'Registration received. In development, the verification code is printed in the server terminal.')
            else:
                messages.success(request, 'Registration received. Check your email for the verification code.')
            return redirect('accounts:verify_otp')
    return render(request, 'accounts/register.html', {'form': form})

@ratelimit(key='ip', rate='3/m', method='POST', block=True)
@ensure_csrf_cookie
def verify_otp(request):
    email = request.session.get('pending_email') or request.POST.get('email', '').strip().lower()
    form = OTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid() and email:
        user = get_object_or_404(User, email=email); otp = user.otps.filter(used_at__isnull=True).order_by('-created_at').first()
        if otp and otp.is_valid() and check_password(form.cleaned_data['code'], otp.code_hash):
            otp.used_at = __import__('django.utils.timezone', fromlist=['now']).now(); otp.save(update_fields=['used_at']); user.is_email_verified = True; user.save(update_fields=['is_email_verified']); messages.success(request, 'Email verified. Sign in after your account is approved.'); request.session.pop('pending_email', None); return redirect('accounts:login')
        form.add_error('code', 'Invalid or expired verification code.')
    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': email})

@ratelimit(key='ip', rate='3/m', method='POST', block=True)
@ensure_csrf_cookie
def resend_otp(request):
    email = request.session.get('pending_email')
    if request.method == 'POST' and email:
        user = User.objects.filter(email=email, is_email_verified=False).first()
        if user:
            try:
                send_otp(user)
            except (OSError, SMTPException) as exc:
                logger.exception('OTP resend failed for %s: %s', email, exc)
                messages.error(request, 'We could not send a new code. Please try again in a minute.')
            else:
                messages.success(request, 'A new verification code was sent. Check Spam or Promotions if it is not in your Inbox.')
        else:
            messages.error(request, 'This verification session has expired. Please register again.')
    return redirect('accounts:verify_otp')

def send_otp(user):
    code = f'{secrets.randbelow(1000000):06d}'
    user.otps.filter(used_at__isnull=True).update(used_at=__import__('django.utils.timezone', fromlist=['now']).now())
    EmailOTP.objects.create(user=user, code_hash=make_password(code))
    send_mail('Smart Campus email verification', f'Your verification code is {code}. It expires in 10 minutes.', settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)

@require_POST
def logout_view(request): logout(request); return redirect('accounts:login')
def home(request): return redirect('dashboard:home') if request.user.is_authenticated else redirect('accounts:login')

@require_http_methods(['GET'])
@login_required
def profile(request):
    photo_data = ''
    if request.user.profile_photo:
        image_format = Image.open(BytesIO(request.user.profile_photo)).format.lower()
        mime_type = {'jpg': 'jpeg'}.get(image_format, image_format)
        photo_data = f'data:image/{mime_type};base64,' + base64.b64encode(request.user.profile_photo).decode()
    return render(request, 'accounts/profile.html', {'profile_photo': photo_data})
