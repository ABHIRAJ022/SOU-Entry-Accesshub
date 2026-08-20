from django.urls import path
from . import views
app_name = 'dashboard'
urlpatterns = [path('', views.home, name='home'), path('map/', views.campus_map, name='campus_map'), path('users/<int:user_id>/approval/', views.approve_user, name='approve_user'), path('students/lookup/', views.student_lookup, name='student_lookup'), path('tokens/generate/', views.issue_token, name='issue_token'), path('tokens/regenerate/', views.regenerate_token, name='regenerate_token'), path('tokens/<uuid:token_id>/status/', views.token_status, name='token_status'), path('tokens/<uuid:token_id>/pdf/', views.token_pdf, name='token_pdf')]
