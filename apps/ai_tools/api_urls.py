"""ai_tools/api_urls.py"""

from django.urls import path
from . import api_views

urlpatterns = [
    path('generate/', api_views.GenerateExercisesAPIView.as_view(), name='api_generate'),
    path('grammar/', api_views.GrammarCheckAPIView.as_view(), name='api_grammar'),
    path('chatbot/', api_views.ChatbotAPIView.as_view(), name='api_chatbot'),
    path('templates/', api_views.TemplateListAPIView.as_view(), name='api_templates'),
]
