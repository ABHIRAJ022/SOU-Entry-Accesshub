from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import User

class CampusSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.account.provider == 'google' and sociallogin.account.extra_data.get('email_verified') is not True:
            return
        email = (sociallogin.user.email or '').lower()
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
                user.is_email_verified = True; user.save(update_fields=['is_email_verified'])
            except User.DoesNotExist:
                pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if sociallogin.account.extra_data.get('email_verified') is True:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
        return user
