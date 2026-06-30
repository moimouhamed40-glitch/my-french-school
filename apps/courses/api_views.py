"""courses/api_views.py"""

from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Course, Lesson, Enrollment, CourseProgress


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'level', 'teacher_name',
                  'enrolled_count', 'is_free', 'duration_hours', 'created_at']

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username

    def get_enrolled_count(self, obj):
        return obj.enrollments.count()


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_type', 'order', 'video_url',
                  'duration_minutes', 'is_free_preview']


class CourseListAPIView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True)
        level = self.request.query_params.get('level')
        if level:
            qs = qs.filter(level=level)
        return qs


class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Course.objects.filter(is_published=True)


class LessonListAPIView(generics.ListAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lesson.objects.filter(course_id=self.kwargs['course_id'])


class EnrollAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        course = generics.get_object_or_404(Course, pk=course_id, is_published=True)
        _, created = Enrollment.objects.get_or_create(
            student=request.user, course=course
        )
        return Response({'enrolled': True, 'created': created})


class ProgressAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        enrollments = Enrollment.objects.filter(student=request.user).select_related('course')
        data = []
        for enr in enrollments:
            total = enr.course.lessons.count()
            done = CourseProgress.objects.filter(
                student=request.user, lesson__course=enr.course
            ).count()
            data.append({
                'course': enr.course.title,
                'slug': enr.course.slug,
                'progress': int((done / total * 100) if total else 0),
                'completed': enr.is_completed,
            })
        return Response(data)
