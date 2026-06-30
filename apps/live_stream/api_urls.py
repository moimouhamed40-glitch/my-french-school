"""live_stream/api_urls.py"""

from django.urls import path
from . import api_views

urlpatterns = [
    path('sessions/', api_views.SessionListAPIView.as_view()),
    path('sessions/<uuid:uid>/', api_views.SessionDetailAPIView.as_view()),
    path('sessions/<uuid:uid>/chat/', api_views.ChatHistoryAPIView.as_view()),
    path('sessions/<uuid:uid>/polls/', api_views.PollListAPIView.as_view()),
]
