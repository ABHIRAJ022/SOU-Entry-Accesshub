from django.urls import path
from . import views
app_name = 'accounts'
urlpatterns = [path('login/', views.login_view, name='login'), path('guest-request/', views.guest_request, name='guest_request'), path('logout/', views.logout_view, name='logout'), path('register/', views.register, name='register'), path('verify-otp/', views.verify_otp, name='verify_otp'), path('resend-otp/', views.resend_otp, name='resend_otp'), path('profile/', views.profile, name='profile')]
