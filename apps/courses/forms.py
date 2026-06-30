"""courses/forms.py"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Course, Lesson, Exercise, ForumThread, ForumReply


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'thumbnail', 'level',
                  'category', 'is_published', 'is_free', 'duration_hours']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'duration_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'lesson_type', 'description', 'video_url',
                  'video_file', 'content', 'duration_minutes', 'is_free_preview']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'lesson_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['title', 'exercise_type', 'question', 'content_data',
                  'correct_answer', 'explanation', 'points']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'exercise_type': forms.Select(attrs={'class': 'form-select'}),
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                  'placeholder': 'JSON data'}),
            'correct_answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ForumThreadForm(forms.ModelForm):
    class Meta:
        model = ForumThread
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control',
                                           'placeholder': _('Titre de la discussion')}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        }


class ForumReplyForm(forms.ModelForm):
    class Meta:
        model = ForumReply
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                         'placeholder': _('Votre réponse...')}),
        }
