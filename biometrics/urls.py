from django.urls import path
from . import views

app_name = 'biometrics'
urlpatterns = [
    path('enroll/', views.enrollment_page, name='enroll_page'),
    path('enroll/submit/', views.enroll, name='enroll'),
    path('verify/live/', views.verification_page, name='verify_page'),
    path('verify/', views.verify, name='verify'),
    path('login-verify/', views.login_verify, name='login_verify'),
]
