import re
from bleach import clean
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def sanitized(value):
    return clean(value or '', tags=[], attributes={}, strip=True).strip()

class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=12)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=12)
    class Meta:
        model = User; fields = ('email', 'full_name', 'enrollment_number', 'phone_number')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs['class'] = 'form-control'
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
        if not re.fullmatch(r'[A-Z0-9-]{3,32}', value): raise ValidationError('Use 3-32 letters, numbers, or hyphens.')
        return value
    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'): raise ValidationError('Passwords do not match.')
        return data
    def save(self, commit=True):
        user = super().save(commit=False); user.set_password(self.cleaned_data['password1'])
        if commit: user.save()
        return user

class SecureLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'email', 'placeholder': 'you@campus.edu'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'autocomplete': 'current-password', 'placeholder': 'Your password'})
    def clean(self):
        email = sanitized(self.cleaned_data.get('username')).lower(); password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None: raise ValidationError('Invalid email or password.')
            if not self.user_cache.is_active: raise ValidationError('This account is inactive.')
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
