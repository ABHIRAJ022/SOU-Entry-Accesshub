from django.urls import path
from . import views

urlpatterns = [
    path('', views.locations_api, name='locations_api'),
    path('create/', views.create_location, name='create_location'),
    path('<int:location_id>/', views.update_location, name='update_location'),
    path('<int:location_id>/delete/', views.delete_location, name='delete_location'),
]