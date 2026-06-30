"""ai_tools/api_views.py"""

from rest_framework import generics, permissions, serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AITemplate
from .utils import generate_exercises, correct_grammar_spacy, get_chatbot_response


class AITemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITemplate
        fields = ['id', 'title', 'template_type', 'level', 'prompt_template',
                  'variables', 'usage_count']


class GenerateExercisesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_teacher and not request.user.is_platform_admin:
            return Response({'error': 'Teachers only'}, status=403)

        grammar_rule = request.data.get('grammar_rule', '')
        level = request.data.get('level', 'A1')
        exercise_type = request.data.get('exercise_type', 'mcq')
        count = int(request.data.get('count', 10))

        if not grammar_rule:
            return Response({'error': 'grammar_rule required'}, status=400)

        result = generate_exercises(
            grammar_rule=grammar_rule,
            level=level,
            exercise_type=exercise_type,
            count=count,
            teacher=request.user,
        )
        return Response(result)


class GrammarCheckAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'text required'}, status=400)
        result = correct_grammar_spacy(text)
        return Response(result)


class ChatbotAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '').strip()
        history = request.data.get('history', [])
        if not message:
            return Response({'error': 'message required'}, status=400)

        user_level = getattr(request.user, 'level', 'A1') or 'A1'
        result = get_chatbot_response(history, message, user_level)
        return Response(result)


class TemplateListAPIView(generics.ListAPIView):
    serializer_class = AITemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AITemplate.objects.all()
        template_type = self.request.query_params.get('type')
        if template_type:
            qs = qs.filter(template_type=template_type)
        return qs
