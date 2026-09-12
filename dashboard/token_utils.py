import base64
import hashlib
import hmac
import json
import textwrap
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


INSTITUTION_LOGO_DESCRIPTION = (
    "Silver Oak University logo: a green circular seal with a stylized tree and "
    "the words 'SILVER OAK UNIVERSITY', paired with the maroon 'SILVER OAK "
    "UNIVERSITY' wordmark and 'EDUCATION TO INNOVATION' tagline, plus a gold "
    "NAAC-accredited 'A' emblem."
)
INSTITUTION_LOGO_PATH = Path(settings.BASE_DIR) / 'static' / 'images' / 'silver-oak-university-logo.png'


def institution_logo_bytes():
    return INSTITUTION_LOGO_PATH.read_bytes()


def signed_payload(token):
    payload = {
        'token_id': str(token.public_id),
        'user_id': str(token.user_id) if token.user_id else None,
        'guest_request_id': str(token.guest_request_id) if token.guest_request_id else None,
        'generation': token.generation,
        'expires_at': token.expires_at.isoformat(),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode()).decode().rstrip('=')
    signature = hmac.new(settings.SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f'{encoded}.{signature}'


def verify_signed_payload(value):
    try:
        encoded, signature = value.rsplit('.', 1)
    except ValueError:
        return None
    expected = hmac.new(settings.SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def token_from_signed_payload(value):
    payload = verify_signed_payload(value)
    if not payload:
        return None
    from .models import CampusToken
    return CampusToken.objects.filter(
        public_id=payload.get('token_id'),
        user_id=payload.get('user_id'),
        guest_request_id=payload.get('guest_request_id'),
    ).select_related('user__branch', 'guest_request').only(
        'id', 'public_id', 'user_id', 'guest_request_id', 'token_hash', 'created_at',
        'expires_at', 'duration_minutes', 'generation', 'revoked_at', 'used_at',
        'user__full_name', 'user__email', 'user__phone_number', 'user__profile_photo',
        'user__enrollment_number', 'user__branch_id', 'user__branch__name',
        'guest_request__name', 'guest_request__email', 'guest_request__mobile',
        'guest_request__gender', 'guest_request__purpose', 'guest_request__live_photo',
    ).first()


@lru_cache(maxsize=512)
def _qr_png_for_payload(payload):
    image = qrcode.make(payload)
    output = BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def qr_png(token):
    return _qr_png_for_payload(signed_payload(token))


def qr_data_url(token):
    return 'data:image/png;base64,' + base64.b64encode(qr_png(token)).decode()


def pdf_pass(token):
    output = BytesIO()
    document = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    document.setTitle(f'SOU Entry AccessHub Pass {token.public_id}')
    document.setFont('Helvetica-Bold', 20)
    document.drawString(180, height - 64, 'SOU ENTRY ACCESSHUB')
    document.setFont('Helvetica', 10)
    document.drawString(180, height - 82, 'Temporary campus entry pass | All times IST')
    document.setStrokeColorRGB(0.1, 0.25, 0.4)
    document.line(54, height - 98, width - 54, height - 98)
    document.drawImage(
        ImageReader(BytesIO(institution_logo_bytes())),
        54,
        height - 210,
        width=100,
        height=141,
        preserveAspectRatio=True,
        anchor='c',
        mask='auto',
    )
    document.setFont('Helvetica', 7.5)
    logo_description = textwrap.wrap(
        'Institution logo: ' + INSTITUTION_LOGO_DESCRIPTION,
        width=75,
    )
    for line_number, line in enumerate(logo_description):
        document.drawString(180, height - 112 - (line_number * 10), line)
    document.setFont('Helvetica-Bold', 12)
    document.drawString(54, height - 140, 'Visitor details' if token.guest_request_id else 'Student details')
    document.setStrokeColorRGB(0.4, 0.4, 0.4)
    document.rect(width - 174, height - 238, 120, 120)
    audit_snapshot = token.audit.snapshot if hasattr(token, 'audit') else None
    photo = audit_snapshot or (token.user.profile_photo if token.user_id else token.guest_request.live_photo)
    if photo:
        try:
            document.drawImage(ImageReader(BytesIO(photo)), width - 174, height - 238, width=120, height=120, preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception:
            document.setFont('Helvetica', 9)
            document.drawCentredString(width - 114, height - 178, 'PHOTO UNAVAILABLE')
    else:
        document.setFont('Helvetica-Bold', 24)
        initials = ''.join(part[0] for part in token.holder_name.split()[:2]).upper()
        document.drawCentredString(width - 114, height - 178, initials or 'SC')
    document.setFont('Helvetica', 8)
    document.drawCentredString(width - 114, height - 228, 'Guest photo' if token.guest_request_id else 'Student profile photo')
    document.setFont('Helvetica', 11)
    guest = token.guest_request if token.guest_request_id else None
    student = token.user if token.user_id else None
    details = [
        ('Name', token.holder_name),
        ('Email / Mobile', f'{token.holder_email or "Not provided"} / {token.guest_request.mobile if token.guest_request_id else token.user.phone_number}'),
        ('Enrollment number', student.enrollment_number if student and student.enrollment_number else 'Not provided'),
        ('Branch', student.branch.name if student and student.branch_id else 'Not provided'),
        ('Gender', guest.get_gender_display() if guest else 'Not provided'),
        ('Purpose', token.guest_request.purpose if token.guest_request_id else 'Student access'),
        ('Token ID', str(token.public_id)),
        ('Token expiry (IST)', timezone.localtime(token.expires_at).strftime('%Y-%m-%d %H:%M:%S %Z')),
    ]
    y = height - 166
    for label, value in details:
        document.setFont('Helvetica-Bold', 10)
        document.drawString(54, y, f'{label}:')
        document.setFont('Helvetica', 10)
        document.drawString(180, y, str(value)[:90])
        y -= 20
    document.setFont('Helvetica-Bold', 12)
    document.drawString(54, y - 12, 'Signed entry QR')
    qr = ImageReader(BytesIO(qr_png(token)))
    document.drawImage(qr, 54, y - 194, width=150, height=150, preserveAspectRatio=True, mask='auto')
    document.setFont('Helvetica', 8)
    document.drawString(54, 56, 'Security disclaimer: This pass is time-bound, signed, and valid only for the named student.')
    document.drawString(54, 44, 'Present this pass at the campus entry checkpoint. Forged or altered passes are invalid.')
    document.showPage()
    document.save()
    return output.getvalue()