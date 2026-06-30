"""ai_tools/forms.py"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import AITemplate, TeacherProject
from apps.courses.models import Course, Exercise


class ExerciseGeneratorForm(forms.Form):
    EXERCISE_TYPE_CHOICES = [
        ('mcq', _('QCM (Choix Multiple)')),
        ('fill_blank', _('Compléter les trous')),
        ('order_sentence', _('Remettre en ordre')),
        ('free_text', _('Question ouverte')),
    ]
    LEVEL_CHOICES = [('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1')]
    COUNT_CHOICES = [(5, '5'), (10, '10'), (15, '15'), (20, '20')]

    grammar_rule = forms.CharField(
        label=_('Règle grammaticale'),
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ex: le présent de l\'indicatif des verbes en -ER'),
        }),
    )
    level = forms.ChoiceField(
        label=_('Niveau'),
        choices=LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    exercise_type = forms.ChoiceField(
        label=_("Type d'exercice"),
        choices=EXERCISE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    count = forms.ChoiceField(
        label=_("Nombre d'exercices"),
        choices=COUNT_CHOICES,
        initial=10,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    course = forms.ModelChoiceField(
        label=_('Cours associé (optionnel)'),
        queryset=Course.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    save_to_course = forms.BooleanField(
        label=_('Enregistrer les exercices dans le cours'),
        required=False,
        initial=False,
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['course'].queryset = Course.objects.filter(teacher=user)

    def clean_count(self):
        return int(self.cleaned_data['count'])


class GrammarCorrectionForm(forms.Form):
    text = forms.CharField(
        label=_('Texte à corriger'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('Collez ou écrivez votre texte en français ici...'),
        }),
        max_length=5000,
    )


class AITemplateUseForm(forms.Form):
    """Dynamically generated form based on template variables."""

    def __init__(self, template, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for variable in template.variables:
            self.fields[variable] = forms.CharField(
                label=variable.replace('_', ' ').title(),
                widget=forms.TextInput(attrs={'class': 'form-control'}),
            )


class TeacherProjectForm(forms.ModelForm):
    class Meta:
        model = TeacherProject
        fields = ['title', 'description', 'thumbnail', 'project_url', 'tools_used']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'project_url': forms.URLInput(attrs={'class': 'form-control'}),
            'tools_used': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '["ChatGPT", "DALL-E", "ElevenLabs"]',
            }),
        }
