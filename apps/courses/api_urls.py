"""courses/api_urls.py"""

from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.CourseListAPIView.as_view(), name='api_course_list'),
    path('<int:pk>/', api_views.CourseDetailAPIView.as_view(), name='api_course_detail'),
    path('<int:course_id>/lessons/', api_views.LessonListAPIView.as_view(), name='api_lessons'),
    path('enroll/<int:course_id>/', api_views.EnrollAPIView.as_view(), name='api_enroll'),
    path('progress/', api_views.ProgressAPIView.as_view(), name='api_progress'),
]
