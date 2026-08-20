from django.urls import path
from . import views
app_name = 'dashboard'
urlpatterns = [path('', views.home, name='home'), path('users/<int:user_id>/approval/', views.approve_user, name='approve_user'), path('students/lookup/', views.student_lookup, name='student_lookup'), path('tokens/generate/', views.issue_token, name='issue_token'), path('tokens/regenerate/', views.regenerate_token, name='regenerate_token')]
