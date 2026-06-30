from django.urls import path
from . import views

app_name = 'ar_content'

urlpatterns = [
    path('', views.ar_home_view, name='home'),
]