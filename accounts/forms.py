import re
from bleach import clean
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Branch, User

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def sanitized(value):
    return clean(value or '', tags=[], attributes={}, strip=True).strip()

class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=12)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=12)
    security_pin = forms.CharField(label='Student security PIN', min_length=6, max_length=12, required=False, widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=User.Role.choices, label='Account type')
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(is_active=True), required=False, label='Campus branch')
    class Meta:
        model = User; fields = ('role', 'branch', 'email', 'full_name', 'enrollment_number', 'phone_number')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs['class'] = 'form-control'
        self.fields['role'].help_text = 'Choose the campus role that matches your responsibilities.'
        self.fields['branch'].help_text = 'Students must select the branch that manages their enrollment.'
    def clean_email(self):
        value = sanitized(self.cleaned_data['email']).lower()
        if not EMAIL_RE.fullmatch(value): raise ValidationError('Enter a valid email address.')
        return value
    def clean_full_name(self):
        value = sanitized(self.cleaned_data['full_name'])
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,119}", value): raise ValidationError('Enter a valid full name.')
        return value
    def clean_enrollment_number(self):
        value = sanitized(self.cleaned_data['enrollment_number']).upper()
        if not value:
            if self.cleaned_data.get('role') == User.Role.STUDENT:
                raise ValidationError('Enrollment number is required for student accounts.')
            return None
        if not re.fullmatch(r'[A-Z0-9-]{3,32}', value): raise ValidationError('Use 3-32 letters, numbers, or hyphens.')
        return value
    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'): raise ValidationError('Passwords do not match.')
        if data.get('role') == User.Role.STUDENT and not data.get('branch'):
            raise ValidationError('Students must select a campus branch.')
        pin = data.get('security_pin', '')
        if data.get('role') == User.Role.STUDENT and (not pin or not pin.isdigit()):
            raise ValidationError('Students must choose a numeric security PIN.')
        return data
    def save(self, commit=True):
        user = super().save(commit=False); user.set_password(self.cleaned_data['password1'])
        if self.cleaned_data.get('security_pin'):
            user.set_security_pin(self.cleaned_data['security_pin'])
        if commit: user.save()
        return user

class SecureLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    role = forms.ChoiceField(choices=User.Role.choices, label='Sign in as')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(['role', 'username', 'password'])
        self.fields['role'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'you@campus.edu'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'current-password', 'placeholder': 'Your password'})
    def clean(self):
        email = sanitized(self.cleaned_data.get('username')).lower(); password = self.cleaned_data.get('password')
        selected_role = self.cleaned_data.get('role')
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None: raise ValidationError('Invalid email or password.')
            if not self.user_cache.is_active: raise ValidationError('This account is inactive.')
            if self.user_cache.role != selected_role: raise ValidationError('The selected account type does not match this account.')
            if not self.user_cache.can_login: raise ValidationError('Verify your email and await admin approval before signing in.')
        return self.cleaned_data

class OTPForm(forms.Form):
    code = forms.CharField(min_length=6, max_length=6, strip=True)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].widget.attrs.update({'class': 'form-control otp-input', 'inputmode': 'numeric', 'autocomplete': 'one-time-code', 'placeholder': '000000'})
    def clean_code(self):
        value = self.cleaned_data['code']
        if not value.isdigit(): raise ValidationError('OTP must contain six digits.')
        return value
