from django.urls import path
from . import views

app_name = 'biometrics'
urlpatterns = [
    path('verify/live/', views.verification_page, name='verify_page'),
    path('verify-identity/', views.verify_identity, name='verify_identity'),
    path('request-emergency-otp/', views.request_emergency_otp, name='request_emergency_otp'),
]
