from django.urls import path
from . import views

app_name = 'live_stream'

urlpatterns = [
    path('', views.live_list_view, name='list'),
    path('<int:pk>/', views.live_detail_view, name='detail'),
    path('create/', views.create_live_view, name='create'),
]