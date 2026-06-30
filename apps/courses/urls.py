"""courses/urls.py"""

from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list_view, name='list'),
    path('create/', views.create_course_view, name='create'),
    path('library/', views.literary_library_view, name='library'),
    path('library/<int:pk>/', views.literary_text_view, name='literary_text'),
    path('forum/', views.forum_list_view, name='forum'),
    path('forum/thread/<int:thread_id>/', views.forum_thread_view, name='forum_thread'),
    path('forum/new/', views.create_thread_view, name='create_thread'),
    path('<slug:slug>/', views.course_detail_view, name='detail'),
    path('<slug:slug>/enroll/', views.enroll_view, name='enroll'),
    path('<slug:slug>/edit/', views.edit_course_view, name='edit'),
    path('<slug:slug>/add-lesson/', views.add_lesson_view, name='add_lesson'),
    path('<slug:slug>/lesson/<int:lesson_id>/', views.lesson_view, name='lesson'),
    path('<slug:slug>/forum/', views.forum_list_view, name='course_forum'),
    path('<slug:slug>/forum/new/', views.create_thread_view, name='course_create_thread'),
    path('exercise/<int:exercise_id>/submit/', views.submit_exercise_view, name='submit_exercise'),
]
