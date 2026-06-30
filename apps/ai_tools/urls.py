from django.urls import path
from . import views

app_name = 'ai_tools'

urlpatterns = [
    path('', views.ai_home, name='home'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('chatbot/<int:session_id>/', views.chatbot_session_view, name='chatbot_session'),
    path('chatbot/new/', views.new_chatbot_session, name='new_chatbot_session'),
    path('chatbot/send/', views.send_chatbot_message, name='send_chatbot_message'),
    path('exercise-generator/', views.exercise_generator, name='exercise_generator'),
    path('generate-exercise/', views.generate_exercise_view, name='generate_exercise'),
    path('grammar-corrector/', views.grammar_corrector, name='grammar_corrector'),
    path('templates-lab/', views.templates_lab, name='templates_lab'),
    path('training-hub/', views.training_hub, name='training_hub'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('submit-project/', views.submit_project_view, name='submit_project'), 
     path('generate-lesson/', views.generate_lesson_view, name='generate_lesson'),
    path('generate-game/', views.generate_game_view, name='generate_game'),
    path('generate-mindmap/', views.generate_mindmap_view, name='generate_mindmap'), # ✅ أضف هذا
]