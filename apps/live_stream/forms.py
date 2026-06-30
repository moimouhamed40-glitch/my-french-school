"""live_stream/forms.py"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import LiveSession, Poll


class LiveSessionForm(forms.ModelForm):
    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'course', 'scheduled_at', 'max_participants',
                  'enable_chat', 'enable_whiteboard', 'enable_recording']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['question', 'poll_type', 'options']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control'}),
            'poll_type': forms.Select(attrs={'class': 'form-select'}),
            'options': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                             'placeholder': '["Option A","Option B"]'}),
        }
