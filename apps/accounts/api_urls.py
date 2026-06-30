"""accounts/api_urls.py"""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from . import api_views

urlpatterns = [
    path('token/', obtain_auth_token, name='api_token'),
    path('me/', api_views.CurrentUserView.as_view(), name='api_me'),
    path('users/', api_views.UserListView.as_view(), name='api_users'),
    path('users/<int:pk>/', api_views.UserDetailView.as_view(), name='api_user_detail'),
    path('notifications/', api_views.NotificationListView.as_view(), name='api_notifications'),
    path('notifications/<int:pk>/read/', api_views.MarkNotificationReadView.as_view(), name='api_notif_read'),
]
