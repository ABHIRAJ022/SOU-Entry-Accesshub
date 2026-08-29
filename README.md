# Your Campus Token

Your Campus Token is a Django web application for campus access control. It supports student registration and approval, email OTP verification, live identity verification, signed QR token generation, guest visitor approval, security gate scanning, and campus map management. The project is built around a custom user model, per-role access rules, and database-backed token auditing.

## 1. Purpose and product scope

This repository implements a campus access workflow for four primary user groups:

- Students: create accounts, verify their email, wait for admin approval, verify identity, and generate campus entry tokens.
- Branch administrators: review and approve students in their assigned branch.
- Main administrator: approves staff accounts and handles replacement guest requests that require higher-level review.
- Security staff: scan QR-based tokens at the gate and validate visitor/student identification.

The application is primarily a Django server-rendered app with a small amount of JavaScript for camera capture, token countdowns, QR scanner UI, and map routes. It does not contain a separate frontend SPA, API gateway, or AI/ML module.

## 2. Repository status and verification

This README was created from the actual repository state and validated against the project’s Django test suite.

Verified with:

```bash
cd /workspaces/Your-Campus-Token
source .venv/bin/activate
python manage.py test --verbosity 1
```

Result: 62 tests ran and all passed.

## 3. Technology stack

### Core platform

- Python 3.12 in the project environment
- Django 5.1 via the requirement pin `Django>=5.1,<6.0`
- Django ORM for database models and migrations
- Django templates for page rendering
- Django admin for model management and admin workflows

### Authentication and security

- `django-allauth` for Google OAuth login integration and route generation
- Custom `AbstractBaseUser` model in `accounts/models.py`
- `django.contrib.auth` with a custom `UserManager`
- `django-ratelimit` on login and sensitive request routes
- `django-csp` and `django-cors-headers` for CSP and CORS controls
- `django.middleware.csrf.CsrfViewMiddleware` with custom `CSRF_COOKIE_NAME = 'campus_csrftoken_v2'`
- `whitenoise` for static file serving
- `argon2-cffi` via `Argon2PasswordHasher` for password hashing
- `django.contrib.auth.password_validation` validators with minimum 12-character passwords
- `django-simple` style session and HTTP security configuration from `config/settings.py`

### Data and storage

- SQLite by default for local development (`config/settings_local.py`)
- PostgreSQL support when `DATABASE_URL` is set in production (`config/settings.py`)
- `dj-database-url` is installed, but the app explicitly validates a PostgreSQL URL when the setting is used
- `Pillow` for image verification and profile photo processing
- `cloudinary_storage` and `Cloudinary` support for media storage when `CLOUDINARY_URL` is configured
- `openpyxl` for Excel report generation in `core/reports.py`
- `reportlab` for PDF pass generation in `dashboard/token_utils.py`
- `qrcode` for QR code generation

### Web and frontend

- Bootstrap 5 via CDN in templates
- Leaflet + OpenStreetMap tiles for the campus map UI
- `html5-qrcode` for the gate scanner in the security dashboard
- Static JavaScript under `static/js/` for camera capture, token generation, validation and UI updates

### Network, email and integrations

- `requests` is installed but not used in this codebase as a direct integration dependency
- Django SMTP email backend with console fallback in development
- Google OAuth app configuration via environment variables and allauth
- OSRM router API for walking directions in `static/js/campus_map.js`
- No AI/ML library or provider integration was found in the repository

## 4. High-level architecture

```mermaid
flowchart TD
    Browser[Browser / staff device] --> Login[Login, registration, OTP, guest access]
    Browser --> TokenFlow[Student dashboard and token issuance]
    Browser --> ScanFlow[Security gate scanner]
    Browser --> MapFlow[Campus map and route generation]

    Login --> Accounts[accounts app]
    TokenFlow --> Dashboard[dashboard app]
    ScanFlow --> Dashboard
    MapFlow --> Dashboard
    Login --> Biometrics[biometrics app]

    Accounts --> UserModel[User / Branch / OTP models]
    Dashboard --> TokenModels[CampusToken / GuestTokenRequest / TokenAudit / CampusLocation]
    Biometrics --> IdentityModel[IdentityVerification model]

    TokenModels --> QR[Signed QR payload]
    QR --> SecurityValidate[validate_token endpoint]
    SecurityValidate --> AccessDecision[Allow or reject campus access]

    Dashboard --> PDF[PDF pass generation]
    Accounts --> Mail[SMTP / console email]
    Core[core app] --> Audit[Audit log + health checks + SEO middleware]
```

## 5. Actual repository structure

```text
Your-Campus-Token/
├── .env
├── .env.example
├── .git/
├── .gitignore
├── .venv/
├── README.md
├── accounts/
│   ├── __init__.py
│   ├── adapters.py
│   ├── admin.py
│   ├── forms.py
│   ├── managers.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_user_is_approved_by_super_admin_branch_user_branch.py
│   │   ├── 0003_user_security_pin_hash.py
│   │   └── 0004_user_profile_photo.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── api/
│   ├── __init__.py
│   └── index.py
├── biometrics/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   └── 0002_identity_verification.py
│   ├── models.py
│   ├── snapshots.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── settings_local.py
│   ├── urls.py
│   └── wsgi.py
├── core/
│   ├── __init__.py
│   ├── admin.py
│   ├── context_processors.py
│   ├── management/
│   │   └── commands/
│   │       └── check_email.py
│   ├── middleware.py
│   ├── migrations/
│   │   └── 0001_auditlog.py
│   ├── models.py
│   ├── reports.py
│   ├── seo.py
│   ├── static_storage.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── dashboard/
│   ├── __init__.py
│   ├── admin.py
│   ├── location_urls.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_tokenaudit.py
│   │   ├── 0003_campustoken_phase3.py
│   │   ├── 0004_phase4.py
│   │   ├── 0005_alter_campustoken_user_guesttokenrequest_and_more.py
│   │   ├── 0006_remove_campustoken_token_has_owner_and_more.py
│   │   ├── 0007_guesttokenrequest_gender_and_more.py
│   │   ├── 0008_alter_guesttokenrequest_status.py
│   │   └── 0009_alter_guesttokenrequest_status.py
│   ├── models.py
│   ├── notifications.py
│   ├── tests.py
│   ├── token_utils.py
│   ├── urls.py
│   └── views.py
├── static/
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── campus_map.js
│       ├── csrf_refresh.js
│       ├── dashboard.js
│       ├── face_capture.js
│       ├── guest_request.js
│       ├── health_check.js
│       ├── register.js
│       ├── security_scanner.js
│       ├── theme.js
│       └── timezone.js
├── staticfiles/
│   ├── ... generated static output
├── templates/
│   ├── accounts/
│   │   ├── guest_request.html
│   │   ├── login.html
│   │   ├── profile.html
│   │   ├── register.html
│   │   └── verify_otp.html
│   ├── admin/
│   │   └── base_site.html
│   ├── base.html
│   ├── biometrics/
│   │   └── enroll.html
│   ├── csrf_failure.html
│   ├── dashboard/
│   │   ├── admin.html
│   │   ├── campus_map.html
│   │   ├── guest_request_detail.html
│   │   ├── guest_requests.html
│   │   ├── security.html
│   │   ├── student.html
│   │   ├── token_history.html
│   │   └── tokens.html
│   └── socialaccount/
├── build_files.sh
├── db.sqlite3
├── manage.py
├── requirements.txt
├── vercel.json
└── staticfiles/
```

Note: `staticfiles/` is generated output and is not documented in detail. There are no Docker, CI/CD workflow files, or AI model configuration files in the repository.

## 6. Application modules and responsibilities

### 6.1 accounts app

Purpose: user lifecycle, authentication, role validation and OTP-based sign-up.

Files and responsibilities:

| File | Responsibility |
| --- | --- |
| `accounts/models.py` | Defines `Branch`, `User`, and `EmailOTP`. Custom login gating and security PIN logic live here. |
| `accounts/managers.py` | Custom `UserManager` for creating normal users and superusers. |
| `accounts/forms.py` | Registration, login, guest request, and OTP form validation. Includes sanitization and password security checks. |
| `accounts/views.py` | Login, registration, OTP verification, resend OTP, guest request submission, logout, profile page. |
| `accounts/urls.py` | All user-facing account routes. |
| `accounts/adapters.py` | `CampusSocialAccountAdapter` connects Google social login to the custom `User` model and marks email as verified. |
| `accounts/admin.py` | Django admin registration for `Branch`, `EmailOTP`, and `User`. |

Key runtime behavior:

- `User` uses `email` as `USERNAME_FIELD`.
- `can_login` only allows access when the user email is verified and approval is complete:
  - Students require branch assignment and admin approval.
  - Staff roles require super-admin approval.
- Passwords are hashed using `Argon2PasswordHasher` first and then `PBKDF2PasswordHasher` fallback.
- `SecureLoginForm.clean()` enforces selected-role equality with the authenticated user role.
- `RegistrationForm` validates email, password match, security pin for students, branch selection, and allowed enrollment format.

### 6.2 dashboard app

Purpose: token issuance, guest access, admin approval, gate validation, location management, and dashboards.

Files and responsibilities:

| File | Responsibility |
| --- | --- |
| `dashboard/models.py` | `CampusToken`, `GuestTokenRequest`, `TokenAudit`, `CampusLocation`, `TokenNotification`. |
| `dashboard/views.py` | Dashboard pages, admin actions, guest approvals, token validation, location APIs, token status/PDF views. |
| `dashboard/urls.py` | All dashboard pages and direct routes. |
| `dashboard/location_urls.py` | `/api/locations/*` routes. |
| `dashboard/token_utils.py` | QR signing, verification, and PDF generation. |
| `dashboard/notifications.py` | Email notification sending for approvals and token expiry. |
| `dashboard/admin.py` | Django admin for token and guest records. |

Important model behavior:

- `CampusToken.issue(user, duration_minutes=60)` enforces:
  - one active token at a time per user
  - max 3 tokens per day
  - generation counter increase
  - automatic revocation of expired non-used tokens
- `CampusToken.issue_for_guest(guest_request)` creates a guest token using the visitor request and duration.
- `CampusToken.is_active` is true only when not revoked and before expiry.
- `TokenAudit` stores the verification snapshot and method during token issuance.
- `GuestTokenRequest` tracks status transitions: `PENDING`, `MAIN_ADMIN_REQUIRED`, `APPROVED`, `REJECTED`, `CANCELLED`.
- `CampusLocation` stores map coordinates and metadata for the campus navigation system.

### 6.3 biometrics app

Purpose: live webcam identity verification before a student can create a token.

Files and responsibilities:

| File | Responsibility |
| --- | --- |
| `biometrics/models.py` | `IdentityVerification` model with snapshot, verification method and expiry time. |
| `biometrics/snapshots.py` | `process_webcam_snapshot()` validates and compresses live webcam photos. |
| `biometrics/views.py` | `verification_page`, `verify_identity`, and emergency OTP generation. |
| `biometrics/urls.py` | Identity verification routes. |
| `biometrics/admin.py` | Admin registration for identity verification records. |

Validation rules:

- Only JPEG webcam captures are accepted.
- Images must be at least 320x240 pixels.
- Files over 200 KB are rejected.
- Brightness is checked to reject dark or overexposed images.
- A valid session capture ID and timestamp are required.
- Users must be authenticated, verified, and approved before verification.

### 6.4 core app

Purpose: platform cross-cutting concerns.

Files and responsibilities:

| File | Responsibility |
| --- | --- |
| `core/models.py` | `AuditLog` model stores immutable audit entries. |
| `core/middleware.py` | Security headers and audit event logging. |
| `core/views.py` | Health check, CSRF recovery page, and static asset route. |
| `core/seo.py` | `robots.txt` and `sitemap.xml` output. |
| `core/context_processors.py` | SEO metadata injection. |
| `core/reports.py` | CSV/XLSX/JSON exports for audit and token data. |
| `core/urls.py` | Admin-only report endpoints. |
| `core/static_storage.py` | Non-strict static manifest storage for whitenoise. |
| `core/management/commands/check_email.py` | Validates SMTP configuration and tests the connection. |

### 6.5 config app

Purpose: environment-driven application settings and global routing.

Files and responsibilities:

| File | Responsibility |
| --- | --- |
| `config/settings.py` | Main settings: environment loading, security, auth backends, middleware, database config, email config, static/media config, CORS and CSP, Google auth, and production enforcement. |
| `config/settings_local.py` | Local SQLite/dev settings with console email backend. |
| `config/urls.py` | Top-level URL includes for accounts, dashboard, admin, health endpoint, and Google auth routes. |
| `config/asgi.py` | ASGI app wiring. |
| `config/wsgi.py` | WSGI app wiring for Vercel and general deployment. |

## 7. Data model architecture

### 7.1 Core database models

| Model | Table role | Important fields | Relationships |
| --- | --- | --- | --- |
| `User` | Custom authentication/account model | `email`, `full_name`, `role`, `branch`, `enrollment_number`, `security_pin_hash`, approval flags, profile photo | One-to-many with `EmailOTP`, `CampusToken`, `TokenAudit`, `CampusLocation`, `AuditLog` |
| `Branch` | Campus branch repository | `name`, `code`, `assigned_admin`, `is_active` | One-to-one assignment to admin; one-to-many members |
| `EmailOTP` | One-time registration and identity codes | `code_hash`, `created_at`, `attempts`, `used_at` | Many-to-one `User` |
| `CampusToken` | Issued token record | `public_id`, `token_hash`, `expires_at`, `duration_minutes`, `generation`, `revoked_at`, `used_at`, `used_by` | One-to-one with `GuestTokenRequest`; many-to-one `User` |
| `GuestTokenRequest` | Visitor request record | `name`, `gender`, `email`, `mobile`, `purpose`, `live_photo`, `status`, `approved_by`, `approved_at` | One-to-one with `CampusToken` |
| `TokenAudit` | Security validation proof | `snapshot`, `snapshot_size`, `verification_method` | One-to-one with `CampusToken`; many-to-one `User` |
| `IdentityVerification` | Live face verification record | `audit_snapshot`, `snapshot_size`, `verification_method`, `expires_at` | Many-to-one `User` |
| `CampusLocation` | Map points | `name`, `category`, `latitude`, `longitude`, `description`, `building_code`, `is_active` | Many-to-one `created_by` user |
| `TokenNotification` | Email reminder tracking | `kind`, `sent_at` | Many-to-one `CampusToken` |
| `AuditLog` | App-level event log | `event`, `action`, `status`, `ip_address`, `user_agent`, `path`, `metadata` | Optional many-to-one `User` |

### 7.2 Database configuration

`config/settings.py` chooses the database as follows:

- If `DATABASE_URL` is present and uses PostgreSQL, Django connects to PostgreSQL with `ENGINE = 'django.db.backends.postgresql'`.
- If no `DATABASE_URL` is set, it falls back to SQLite at `db.sqlite3`.
- Local dev config in `config/settings_local.py` forces SQLite and console email backend.

### 7.3 Migrations

Migrations are present under `accounts/migrations`, `dashboard/migrations`, `biometrics/migrations`, and `core/migrations` and reflect the model evolution over time, including:

- branch assignment and super-admin approval flags
- security pin hashing
- profile photo field
- token audit model and guest token adjustments
- guest request status changes and `MAIN_ADMIN_REQUIRED`

### 7.4 Query and data integrity rules

The application enforces several integrity rules in Python and the database:

- `CampusToken` has a check constraint guaranteeing exactly one owner: either a `user` or a `guest_request`.
- `CampusToken.issue()` rejects a second active token for the same user.
- `CampusToken.DAILY_LIMIT = 3` limits generation to three tokens per day.
- `GuestTokenRequest` prevents a second active token request for the same mobile number while the previous one remains valid.
- `AuditLog.save()` raises `ValueError` if an existing row is edited, making the log immutable after creation.

## 8. Authentication and authorization model

### 8.1 User roles and approval flow

Roles are defined in `accounts/models.py`:

- `ADMIN`
- `STUDENT`
- `SECURITY`

Approval logic:

- Students require `branch` selection and approval by their branch admin (`is_approved_by_admin`).
- Staff accounts require super-admin approval (`is_approved_by_super_admin`).
- Authenticated users are blocked from login unless `user.can_login` is true.
- `SecureLoginForm` validates selected role and ensures role matches account.

### 8.2 Passwords, sessions, cookies and security

From `config/settings.py`:

- `PASSWORD_HASHERS` = Argon2 then PBKDF2.
- Session cookies are HTTP-only and secure in production.
- CSRF cookies are separate with custom name `campus_csrftoken_v2`.
- `SESSION_COOKIE_AGE = 1800` and `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`.
- `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*`, `SESSION_COOKIE_SECURE`, and `CSRF_COOKIE_SECURE` are enabled in production.
- `X_FRAME_OPTIONS = 'DENY'` and `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'`.
- `core.middleware.SecurityHeadersMiddleware` adds `Permissions-Policy`, `Referrer-Policy`, and disables caching for HTML pages.

### 8.3 Authentication routes

Routes defined in `accounts/urls.py`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/accounts/login/` | Sign-in view |
| `POST` | `/accounts/login/` | Validate credentials and login |
| `GET` | `/accounts/register/` | Registration page |
| `POST` | `/accounts/register/` | Submit user and trigger OTP email |
| `GET` | `/accounts/verify-otp/` | OTP entry page |
| `POST` | `/accounts/verify-otp/` | Validate OTP and mark email as verified |
| `POST` | `/accounts/resend-otp/` | Resend verification code |
| `POST` | `/accounts/logout/` | Logout |
| `GET` | `/accounts/profile/` | Read-only profile page |
| `GET` | `/accounts/guest-request/` | Guest access form |
| `POST` | `/accounts/guest-request/` | Submit guest access request |

Google social login routes are generated through `django-allauth` and mounted under `/accounts/` as part of `config/urls.py`.

### 8.4 Authorization decorators

Authorization in `dashboard/views.py` is enforced with decorators:

- `role_required(*roles)` for student/admin/security access
- `_guest_staff_required` for guest queue operations
- `_token_viewer_required` for token viewer endpoints

Examples:

- only `ADMIN` can manage student approval pages
- only `SECURITY` or `is_superuser` can review guest requests
- only `STUDENT`, `SECURITY`, or superuser can access token status/PDF pages under specific conditions

## 9. Major business flows

### 9.1 Student registration and email verification

Flow:

1. User visits `/accounts/register/`.
2. `RegistrationForm` validates branch, password, security pin, and enrollment number rules.
3. `accounts/views.register()` creates a `User`, sends OTP via `send_otp()`, stores `pending_email` in session, and redirects to `/accounts/verify-otp/`.
4. `verify_otp()` checks the latest un-used OTP and validates it with `check_password()`.
5. If valid, the user’s `is_email_verified` flag is set to true.
6. The user can only sign in once the approval rules are satisfied.

### 9.2 Identity verification

Routes:

- `/api/verify/live/` renders the biometric page
- `/api/verify-identity/` validates a live JPEG webcam capture
- `/api/request-emergency-otp/` sends a four-digit verification code

Technician logic:

- `biometrics.views.verify_identity()` validates JSON request payload.
- It checks capture mode, `capture_id`, timestamp freshness, and image MIME format.
- The image is passed to `process_webcam_snapshot()` in `biometrics/snapshots.py`.
- The user must complete either:
  - numeric security PIN check (`user.check_security_pin()`), or
  - 4-digit emergency OTP verification
- On success, an `IdentityVerification` record is created with expiry from `IDENTITY_VERIFICATION_MAX_AGE_SECONDS`.
- The session stores verification status for later token creation.

### 9.3 Student token issuance

Routes:

- `POST /dashboard/tokens/generate/`
- `POST /dashboard/tokens/regenerate/`

Process:

1. The student must be authenticated and `can_login` must be true.
2. The request body is JSON and must include a valid `duration_minutes` and a webcam photo.
3. `process_webcam_snapshot(payload)` validates the image is a live frame.
4. `CampusToken.issue(user, duration_minutes)` checks the daily limit, active token, and token expiry cleanup.
5. `TokenAudit` records the user, snapshot, and verification method.
6. `send_token_created(token)` emails a signed PDF pass and attaches it to the email.
7. The response returns:
   - raw token string
   - public token ID
   - generation number
   - expiry timestamp
   - signed QR payload
   - data URL for QR image
   - PDF and status URLs

### 9.4 Security QR validation and gate scanning

Route:

- `POST /api/tokens/validate/`

Process:

1. Security staff open the scanner page at `/dashboard/security/`.
2. The browser uses `html5-qrcode` to scan a QR string.
3. The scanned QR is posted to `/api/tokens/validate/`.
4. `token_from_signed_payload()` verifies the signed payload using HMAC and `settings.SECRET_KEY`.
5. `validate_token()` checks:
   - valid signature
   - token exists
   - token not expired/revoked/used
   - student is active and `can_login`, or guest request is approved
6. On success it marks the token as used and returns a JSON payload containing the holder’s details and PDF link.
7. In the UI, the result is shown with name, photo, enrollment, purpose, expiry, and token ID.

### 9.5 Guest and visitor request flow

Routes:

- `GET /accounts/guest-request/`
- `POST /accounts/guest-request/`
- `GET /dashboard/guest-requests/`
- `GET /dashboard/guest-requests/<request_id>/`
- `POST /dashboard/guest-requests/<request_id>/approve/`
- `POST /dashboard/guest-requests/<request_id>/reject/`

Behavior:

- `GuestTokenRequestForm` validates name, gender, email, mobile, purpose, duration and live photo.
- The app ensures a request is not submitted if the same mobile number already has an active approved guest token.
- If the same mobile has a previous request, the new guest request is set to `MAIN_ADMIN_REQUIRED` instead of `PENDING`.
- Security or the super-admin can approve the request, which creates a `CampusToken` via `CampusToken.issue_for_guest()`.
- Rejected or cancelled guest requests cannot be re-used.

### 9.6 Campus map and location management

Routes:

- `GET /dashboard/map/`
- `GET /api/locations/`
- `POST /api/locations/create/`
- `POST /api/locations/<location_id>/`
- `POST /api/locations/<location_id>/delete/`

Behavior:

- `CampusLocation` records building positions with latitude and longitude.
- `campus_map.html` loads a Leaflet map and markers.
- `campus_map.js` loads `/api/locations/` and displays categories.
- Admin users can create or deactivate campus locations.
- The map UI also calls OSRM route API to estimate walking directions from the user’s current position.

## 10. APIs documented from the actual implementation

### 10.1 Account, dashboard and health endpoints

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/health/` | None | Database health check (`SELECT 1`) |
| `GET` | `/robots.txt` | None | SEO robots file |
| `GET` | `/sitemap.xml` | None | Minimal sitemap |
| `GET` | `/admin-tools/reports/audit.csv` | Superuser + admin role | Download audit CSV |
| `GET` | `/admin-tools/reports/audit.xlsx` | Superuser + admin role | Download audit spreadsheet |
| `GET` | `/admin-tools/reports/audit.json` | Superuser + admin role | Download audit JSON |
| `GET` | `/admin-tools/reports/tokens.csv` | Superuser + admin role | Download token CSV |
| `GET` | `/admin-tools/reports/tokens.xlsx` | Superuser + admin role | Download token spreadsheet |

### 10.2 Student and admin dashboard endpoints

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/dashboard/` | Student/admin/security | Home dashboard |
| `GET` | `/dashboard/security/` | Security | Security dashboard |
| `GET` | `/dashboard/map/` | Student/admin/security | Campus map |
| `GET` | `/dashboard/guest-requests/` | Security or superuser | Guest queue |
| `GET` | `/dashboard/guest-requests/<id>/` | Security or superuser | Guest request detail |
| `POST` | `/dashboard/guest-requests/<id>/approve/` | Security or superuser | Approve guest request and issue token |
| `POST` | `/dashboard/guest-requests/<id>/reject/` | Security or superuser | Reject guest request |
| `GET` | `/dashboard/tokens/manage/` | Admin | Live and expired token lists |
| `GET` | `/dashboard/tokens/history/<user_id>/` | Admin | Per-student token history |
| `POST` | `/dashboard/tokens/<uuid>/cancel/` | Admin | Cancel a live token |
| `POST` | `/dashboard/tokens/generate/` | Student | Issue new token |
| `POST` | `/dashboard/tokens/regenerate/` | Student | Reissue token via same route |
| `GET` | `/dashboard/tokens/<uuid>/status/` | Student or security, or superuser | Get token status |
| `GET` | `/dashboard/tokens/<uuid>/pdf/` | Student or security, or superuser | Download PDF pass |
| `GET` | `/dashboard/students/lookup/` | Security | Student lookup by name or enrollment |
| `POST` | `/dashboard/users/<user_id>/approval/` | Admin | Approve/reject/revoke users |

### 10.3 Biometric and validation endpoints

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/verify/live/` | Login required | Load biometric verification page |
| `POST` | `/api/request-emergency-otp/` | Login required | Send a four-digit emergency code |
| `POST` | `/api/verify-identity/` | Login required | Validate webcam snapshot + security PIN/OTP |
| `POST` | `/api/tokens/validate/` | Security required | Validate QR payload and return profile details |

### 10.4 Location API endpoints

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/locations/` | Student/admin/security | Return all active campus locations |
| `POST` | `/api/locations/create/` | Admin | Create a campus location |
| `POST` | `/api/locations/<location_id>/` | Admin | Update a location |
| `POST` | `/api/locations/<location_id>/delete/` | Admin | Deactivate a location |

### 10.5 Request and response shapes

Examples from actual code:

- Student token issuance response sample:

```json
{
  "token": "<raw_token>",
  "token_id": "<uuid>",
  "generation": 1,
  "expires_at": "2026-08-29T12:34:56+00:00",
  "server_now": "2026-08-29T12:00:00+00:00",
  "qr_payload": "<signed-token-string>",
  "qr_data_url": "data:image/png;base64,...",
  "pdf_url": "/dashboard/tokens/<uuid>/pdf/",
  "status_url": "/dashboard/tokens/<uuid>/status/"
}
```

- Token validation response sample:

```json
{
  "valid": true,
  "token_id": "<uuid>",
  "holder_type": "Student",
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "mobile": "9876543210",
  "branch": "Science Branch",
  "purpose": "Student access",
  "expires_at": "2026-08-29T12:34:56+00:00",
  "profile_photo": "data:image/jpeg;base64,...",
  "pdf_url": "/dashboard/tokens/<uuid>/pdf/"
}
```

- Health check response:

```json
{"status": "operational"}
```

## 11. Frontend and template responsibilities

### Templates

| Template | Purpose |
| --- | --- |
| `templates/base.html` | Shared layout, nav, messages, theme toggle, common scripts |
| `templates/accounts/login.html` | Sign-in screen with Google login link |
| `templates/accounts/register.html` | Account setup and student-only field toggling |
| `templates/accounts/verify_otp.html` | OTP entry form |
| `templates/accounts/guest_request.html` | Guest access request with live camera capture |
| `templates/accounts/profile.html` | Read-only profile view |
| `templates/biometrics/enroll.html` | Identity verification camera UI |
| `templates/dashboard/student.html` | Student dashboard with token generation and history |
| `templates/dashboard/admin.html` | Admin dashboard and approval queue |
| `templates/dashboard/security.html` | Security gate scanner and guest request overview |
| `templates/dashboard/guest_requests.html` | Guest request review list |
| `templates/dashboard/guest_request_detail.html` | Detail page for a single guest request |
| `templates/dashboard/campus_map.html` | Campus map and admin location form |

### JavaScript modules

| File | Main behavior |
| --- | --- |
| `static/js/dashboard.js` | Token countdowns, token action submission, approval actions, guest token persistence |
| `static/js/face_capture.js` | Webcam capture and identity verification request |
| `static/js/guest_request.js` | Guest photo capture and submission |
| `static/js/security_scanner.js` | QR scanning for gate validation |
| `static/js/campus_map.js` | Leaflet rendering, route requests, location creation and deactivation |
| `static/js/register.js` | Show/hide student-only fields |
| `static/js/theme.js` | Theme toggle |
| `static/js/health_check.js` | Health badge logic |
| `static/js/csrf_refresh.js` | CSRF refresh logic |

## 12. Security, validation, logging, and resilience

### Security features in code

- CSRF-protected forms with a custom cookie name and trusted origins support
- Rate limiting on login and sensitive POST actions via `django-ratelimit`
- HTTPS enforcement in production via `SECURE_SSL_REDIRECT`
- Secure cookies and HSTS in production
- `SecurityHeadersMiddleware` adds permission policy and no-store headers for HTML pages
- `django-csp` sets a restrictive CSP in `config/settings.py`
- Input sanitization with `bleach.clean()` for registration and guest request data
- Password validation minimum length 12 characters
- Custom `AuditLog` write path for authentication and token events

### Error handling and validation

- `SnapshotError` converts invalid or missing live image capture into user-facing form errors
- `IdentityError` wraps biometric verification validation and returns JSON errors with status codes
- `validate_token()` returns 400/409/404 for invalid, expired, or missing tokens
- `approve_user()` returns 403 when a branch admin tries to manage another branch
- `register()` catches `SMTPException`, logs failure, and deletes the created user if email delivery fails
- `dashboard/views.py` uses `JsonResponse` for AJAX logic and ensures JSON is returned on validation errors

### Logging and audit trail

- Logging is configured in `config/settings.py` with a console handler for the `accounts` logger.
- `AuditLoggingMiddleware` creates `AuditLog` entries on selected routes.
- `AuditLog` records path, method, user, IP address, browser agent, and action metadata.
- Admin exports are available through `core/reports.py`.

## 13. Environment variables and deployment settings

The project uses environment variables loaded via `python-dotenv` in `config/settings.py`.

Fan-out of the actual environment variables found in the repo:

| Variable | Used in | Purpose | Required? | Example |
| --- | --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | `config/settings.py` | Django secret for signing and cookies | Yes in production | `replace-with-a-long-random-secret` |
| `JWT_SECRET` | `config/settings.py` | JWT-style secret value used for auth/verification fallback | Yes in production | `replace-with-a-random-secret` |
| `DJANGO_DEBUG` | `config/settings.py` | Enables debug mode | No | `False` |
| `DJANGO_ALLOWED_HOSTS` | `config/settings.py` | Allowed hosts list | Yes in production | `localhost,127.0.0.1,*.vercel.app` |
| `DJANGO_SITE_URL` | `config/settings.py` | Base URL for SEO and canonical metadata | No | `https://example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `config/settings.py` | Trusted origins for CSRF | No | `https://example.com` |
| `DJANGO_SECURE_SSL_REDIRECT` | `config/settings.py` | Force HTTPS redirect | No | `True` |
| `DATABASE_URL` | `config/settings.py` | PostgreSQL database URL | Required in production when using Postgres | `postgresql://user:password@host:5432/database?sslmode=require` |
| `EMAIL_HOST` | `config/settings.py` | SMTP host | No | `smtp.gmail.com` |
| `EMAIL_PORT` | `config/settings.py` | SMTP port | No | `587` |
| `EMAIL_HOST_USER` | `config/settings.py` | SMTP username | No | `alerts@example.com` |
| `EMAIL_HOST_PASSWORD` | `config/settings.py` | SMTP password | No | `replace-me` |
| `EMAIL_USE_TLS` | `config/settings.py` | SMTP TLS flag | No | `True` |
| `DEFAULT_FROM_EMAIL` | `config/settings.py` | Sender address for email notifications | No | `no-reply@example.com` |
| `EMAIL_BACKEND` | `config/settings.py` | Email backend selection | No | `django.core.mail.backends.smtp.EmailBackend` |
| `GOOGLE_CLIENT_ID` | `config/settings.py` | Google OAuth client ID | No | `your-google-client-id` |
| `GOOGLE_CLIENT_SECRET` | `config/settings.py` | Google OAuth secret | No | `your-google-client-secret` |
| `GOOGLE_SITE_VERIFICATION` | `config/settings.py` | Verification tag for Google Search Console | No | `example-code` |
| `CLOUDINARY_URL` | `config/settings.py` | Cloudinary media storage URL | Required in production if Cloudinary is used | `cloudinary://key:secret@cloud-name` |
| `MEDIA_URL` | `config/settings.py` | Public media base URL | No | `https://res.cloudinary.com/cloud-name/` |
| `CORS_ALLOWED_ORIGINS` | `config/settings.py` | CORS allowlist | No | `https://example.com` |
| `IDENTITY_MAX_REQUEST_BYTES` | `config/settings.py` | Max JSON size for biometric verification | No | `400000` |
| `IDENTITY_VERIFICATION_MAX_AGE_SECONDS` | `config/settings.py` | Expiration for identity verification | No | `300` |

The repository contains both `.env` (local runtime) and `.env.example` (example values), with a default `DJANGO_SECRET_KEY` fallback that is intentionally not production-safe.

## 14. Deployment and build files

### Build scripts

- `build_files.sh` does the following:

```bash
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
```

This is the deployment build script used by the Vercel configuration.

### Vercel configuration

`vercel.json` declares:

- build command: `bash build_files.sh`
- server entry: `api/index.py`
- route catch-all to `api/index.py`
- security headers at the edge

This project uses a single WSGI entry point via `api/index.py` and expects Vercel Python runtime behavior.

### Netlify / static-hosting note

The repository does not contain a `netlify.toml` file. The earlier placeholder README mentioned one, but it is not present in the repository. That claim is therefore not supported and should be treated as not found.

## 15. Testing strategy

The actual test suite is in:

- `accounts/tests.py`
- `dashboard/tests.py`
- `biometrics/tests.py`
- `core/tests.py`

Areas covered by the tests include:

- login success/failure and role mismatch
- OTP generation, verification and resend flows
- CSRF behavior and trusted origins
- branch-admin restrictions
- student approval/revocation
- token issuance and generation limits
- guest request flow and approval
- security token validation
- PDF generation and email sending
- identity verification and emergency OTP flows
- campus location validation
- health endpoint and robots/sitemap behavior

Command:

```bash
python manage.py test --verbosity 1
```

Verified result: 62 tests passed.

## 16. AI/ML status

No AI or ML integration was found in this repository.

This includes:

- no OpenAI / Azure OpenAI / Anthropic / Gemini / Hugging Face integration
- no model provider config files
- no prompt files or model version configuration files
- no embeddings or vector DB setup
- no AI pipeline or inference code paths

Status: Not found in the repository.

## 17. Known limitations and constraints

- The app uses a custom Django template system, not a modern React/Vue/Next.js frontend.
- The security scanner depends on browser camera support and `html5-qrcode` in the client browser.
- Identity verification is intentionally strict and only accepts live webcam captures.
- Token generation is limited to one active token at a time and only three tokens per day per student.
- Guest token replacement requires a main-admin approval state if the same mobile number previously had an approved request.
- Static media is cloud-enabled only if `CLOUDINARY_URL` is configured; otherwise local storage is used for file system media.
- The repository does not include CI/CD, Docker, Kubernetes manifests, or a deployment pipeline under `.github/workflows`, `docker-compose.yml`, or similar files.

## 18. Dependency map and responsibility matrix

### 18.1 Responsibility matrix

| Area | Primary files | Responsibility |
| --- | --- | --- |
| User authentication | `accounts/models.py`, `accounts/forms.py`, `accounts/views.py` | Accounts, login, OTP, approval gating |
| Role authorization | `dashboard/views.py`, `config/settings.py` | Access guard and protected routes |
| Identity proofing | `biometrics/views.py`, `biometrics/snapshots.py`, `biometrics/models.py` | Webcam validation and security PIN/OTP verification |
| Token lifecycle | `dashboard/models.py`, `dashboard/token_utils.py`, `dashboard/views.py` | Issue, sign, validate, mark used, expire |
| Notifications | `dashboard/notifications.py` | Email to approved users and token holders |
| Reporting | `core/reports.py`, `core/urls.py` | CSV/XLSX/JSON audits and token exports |
| Security posture | `config/settings.py`, `core/middleware.py`, `core/views.py` | Headers, CSRF, static security, health checks |
| Campus map | `dashboard/models.py`, `dashboard/views.py`, `templates/dashboard/campus_map.html`, `static/js/campus_map.js` | Locations and walking routes |
| QA and validation | `accounts/tests.py`, `dashboard/tests.py`, `biometrics/tests.py`, `core/tests.py` | Regression protection |

### 18.2 Module dependency map

```mermaid
flowchart LR
    U[User browser] --> A[accounts app]
    A --> Auth[Custom User + login forms]
    A --> OTP[OTP email + verification]
    A --> Google[Google allauth routes]

    Auth --> D[dashboard app]
    D --> TokenModel[CampusToken model]
    D --> GuestModel[GuestTokenRequest model]
    D --> TokenUtils[Signed QR + PDF generation]
    D --> Email[Notifications]

    U --> V[biometrics app]
    V --> Snapshot[Image validation]
    Snapshot --> Identity[IdentityVerification record]
    Identity --> D

    D --> Map[CampusLocation map feature]
    D --> Validate[Security QR validation]
    Validate --> Audit[TokenAudit record]

    Core[core app] --> Settings[settings.py]
    Core --> Middleware[security and audit middleware]
    Core --> Reports[CSV/XLSX reports]
```

## 19. Where to make changes

Use this map when modifying the app:

### UI and page layout

- `templates/base.html` for shared layout
- `templates/accounts/*.html` for account flows
- `templates/dashboard/*.html` for dashboard and security pages
- `static/js/*.js` for client-only behaviors

### Auth and user logic

- `accounts/models.py` for role and login logic
- `accounts/forms.py` for validation rules
- `accounts/views.py` for login and registration flows
- `config/settings.py` for authentication and security configuration

### Token logic and business rules

- `dashboard/models.py` for token rules and model constraints
- `dashboard/views.py` for route logic and permission checks
- `dashboard/token_utils.py` for QR signature and PDF generation
- `dashboard/notifications.py` for email notifications

### Verification and snapshot rules

- `biometrics/snapshots.py` for image validation thresholds and accepted formats
- `biometrics/views.py` for verification states and emergency OTP logic
- `biometrics/models.py` for identity verification lifetimes

### Database changes

- `accounts/migrations/*`, `dashboard/migrations/*`, `biometrics/migrations/*`, and `core/migrations/*`
- `manage.py migrate` to apply changes
- `python manage.py makemigrations` when modifying models

### Configuration and deployment

- `config/settings.py` for environment and runtime settings
- `config/settings_local.py` for local development behavior
- `.env.example` for environment template values
- `build_files.sh` and `vercel.json` for deployment/build behavior

## 20. Installation and development commands

### Local install

```bash
cd /workspaces/Your-Campus-Token
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Local database setup

```bash
python manage.py migrate
```

### Create a superuser

```bash
python manage.py createsuperuser
```

### Run the app locally

```bash
python manage.py runserver
```

Local URLs:

- http://localhost:8000/
- http://localhost:8000/accounts/login/
- http://localhost:8000/dashboard/
- http://localhost:8000/dashboard/security/

### Run the tests

```bash
python manage.py test --verbosity 1
```

### Production build helper

```bash
bash build_files.sh
```

## 21. Documentation coverage and known gaps

### Covered in this documentation

- overall product purpose and architecture
- actual Django app structure and major responsibilities
- environment settings and database modes
- auth, approval, identity verification, token, guest visitor, and map flows
- all major endpoints implemented in the code
- data model descriptions and relationships
- frontend and JS responsibilities
- deployment/build layout and testing strategy
- exact Where to Make Changes guidance

### Genuine gaps / not found in the repository

- AI/ML integration: Not found in the repository.
- Docker or Kubernetes deployment files: Not found in the repository.
- GitHub Actions or CI/CD workflow files: Not found in the repository.
- Any external SaaS service beyond Google OAuth, SMTP, Cloudinary, and OSRM route access: not present in the repository code as direct integrations.
- Separate OpenAPI/Swagger spec: Not found in the repository.

This documentation was written from the code and configuration present in the repository and reflects the implementation as it actually exists today.
4. Student generates a campus token.
5. Token is shown as a QR pass and can be downloaded as a PDF.
6. Security scans and validates the token.

### Guest flow
1. Guest submits a temporary request with personal and purpose details.
2. Security or admin reviews the request.
3. Approved guest gets access token with QR code and expiry.
4. Token can be canceled if needed.

---

## Main entry files

- manage.py — Django project entry point
- config/settings.py — global configuration
- config/urls.py — project router
- dashboard/views.py — main business logic
- dashboard/models.py — core data models
- accounts/models.py — custom user model
- biometrics/snapshots.py — face and verification image handling
- static/js/dashboard.js — frontend token generation and countdown logic
- templates/dashboard/student.html — student access dashboard
- templates/dashboard/guest_request_detail.html — guest request and token detail UI
- templates/dashboard/guest_requests.html — guest request queue

---

## Summary

Your Campus Token is a full-stack campus access solution that combines secure authentication, identity verification, token-based access validation, guest management, and administrative controls. It is designed for institutions where access must be verified, auditable, and role-aware.

---

## License

This project is intended for academic or institutional deployment and is distributed as a local project repository. Update this section with your project's actual license if needed.