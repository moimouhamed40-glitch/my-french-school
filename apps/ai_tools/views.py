from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import ChatbotSession, ChatbotMessage, AITrainingVideo, AITemplate, AIExerciseGeneration, GrammarCorrectionLog, TeacherProject
import json
import re
import requests


@login_required
def ai_home(request):
    """Page principale des outils IA."""
    return render(request, 'ai_tools/ai_home.html')


@login_required
def chatbot_view(request):
    """Page principale du chatbot."""
    sessions = ChatbotSession.objects.filter(user=request.user).order_by('-updated_at')
    context = {
        'sessions': sessions,
        'current_session': None,
        'messages_list': [],
    }
    return render(request, 'ai_tools/chatbot.html', context)


@login_required
def chatbot_session_view(request, session_id):
    """Page d'une session spécifique."""
    session = get_object_or_404(ChatbotSession, pk=session_id, user=request.user)
    messages_list = ChatbotMessage.objects.filter(session=session).order_by('created_at')
    sessions = ChatbotSession.objects.filter(user=request.user).order_by('-updated_at')
    
    context = {
        'sessions': sessions,
        'current_session': session,
        'messages_list': messages_list,
    }
    return render(request, 'ai_tools/chatbot.html', context)


@login_required
def new_chatbot_session(request):
    """Créer une nouvelle session de chat."""
    if request.method == 'POST':
        session = ChatbotSession.objects.create(
            user=request.user,
            title="Nouvelle conversation"
        )
        return JsonResponse({'session_id': session.pk})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def send_chatbot_message(request):
    """Envoyer un message et obtenir une réponse de l'IA avec Groq."""
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée.')
        return redirect('ai_tools:chatbot')
    
    session_id = request.POST.get('session_id')
    message = request.POST.get('message')
    
    if not message:
        messages.error(request, 'Veuillez écrire un message.')
        return redirect('ai_tools:chatbot')
    
    # Si pas de session, en créer une nouvelle
    if not session_id or session_id == '':
        session = ChatbotSession.objects.create(
            user=request.user,
            title=message[:50] + ('...' if len(message) > 50 else '')
        )
    else:
        session = get_object_or_404(ChatbotSession, pk=session_id, user=request.user)
    
    # Sauvegarder le message de l'utilisateur
    ChatbotMessage.objects.create(
        session=session,
        role='user',
        content=message
    )
    
    # Appel à l'API Groq
    try:
        history = ChatbotMessage.objects.filter(session=session).order_by('created_at')
        messages_list = []
        for msg in history:
            messages_list.append({
                'role': msg.role,
                'content': msg.content
            })
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": messages_list,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            assistant_response = result['choices'][0]['message']['content']
        else:
            error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
            assistant_response = f"Erreur API: {error_msg}"
        
    except Exception as e:
        assistant_response = f"Désolé, une erreur s'est produite. Veuillez réessayer. (Erreur: {str(e)})"
    
    # Sauvegarder la réponse
    ChatbotMessage.objects.create(
        session=session,
        role='assistant',
        content=assistant_response
    )
    
    # Mettre à jour la session
    session.total_messages += 2
    session.tokens_used += len(message) + len(assistant_response)
    if session.title == "Nouvelle conversation" or not session.title:
        session.title = message[:50] + ('...' if len(message) > 50 else '')
    session.save()
    
    return redirect('ai_tools:chatbot_session', session_id=session.pk)


@login_required
def exercise_generator(request):
    """Générateur d'exercices IA."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    return render(request, 'ai_tools/exercise_generator.html')


@login_required
def grammar_corrector(request):
    """Correcteur grammatical IA via Groq."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        
        if not text:
            messages.error(request, 'Veuillez entrer un texte.')
            return render(request, 'ai_tools/grammar_corrector.html')
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Corrige les fautes de grammaire, d'orthographe et de conjugaison dans ce texte français.
            Retourne uniquement le texte corrigé, sans commentaires ni explications.
            
            Texte original :
            {text}
            
            Texte corrigé :
            """
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Tu es un correcteur grammatical expert en français. Tu corriges les fautes et retournes uniquement le texte corrigé."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if response.status_code == 200:
                corrected_text = result['choices'][0]['message']['content'].strip()
                # إزالة أي نص إضافي
                if corrected_text.startswith('Texte corrigé :'):
                    corrected_text = corrected_text.replace('Texte corrigé :', '').strip()
                elif corrected_text.startswith('"') and corrected_text.endswith('"'):
                    corrected_text = corrected_text[1:-1].strip()
                
                request.session['correction_result'] = corrected_text
                request.session['original_text'] = text
                messages.success(request, '✅ Texte corrigé avec succès !')
            else:
                error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
                messages.error(request, f'Erreur API: {error_msg}')
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return render(request, 'ai_tools/grammar_corrector.html')


@login_required
def templates_lab(request):
    """Laboratoire de modèles IA."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    return render(request, 'ai_tools/templates_lab.html')


@login_required
def training_hub(request):
    """Centre de formation IA."""
    videos = AITrainingVideo.objects.all()
    return render(request, 'ai_tools/training_hub.html', {'videos': videos})


@login_required
def gallery_view(request):
    """Galerie des projets enseignants."""
    projects = TeacherProject.objects.filter(is_featured=True)
    return render(request, 'ai_tools/gallery.html', {'projects': projects})


@login_required
def generate_exercise_view(request):
    """Générer des exercices avec l'IA via Groq."""
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée.')
        return redirect('ai_tools:exercise_generator')
    
    grammar_rule = request.POST.get('grammar_rule')
    level = request.POST.get('level', 'A1')
    exercise_type = request.POST.get('exercise_type', 'mcq')
    count = int(request.POST.get('count', 10))
    
    if not grammar_rule:
        messages.error(request, 'Veuillez entrer une règle grammaticale.')
        return redirect('ai_tools:exercise_generator')
    
    prompt = f"""
    Génère {count} exercices de français niveau {level} sur la règle: {grammar_rule}.
    Type: {exercise_type}.
    Retourne uniquement un JSON valide avec cette structure exacte:
    {{"exercises": [{{"question": "", "options": [], "correct_answer": "", "explanation": ""}}]}}
    """
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "Tu es un professeur de français. Réponds uniquement avec du JSON valide."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            content = result['choices'][0]['message']['content']
            
            try:
                exercises_data = json.loads(content)
                exercises = exercises_data.get('exercises', [])
                
                if exercises:
                    request.session['generated_exercises'] = exercises
                    messages.success(request, f'{len(exercises)} exercices générés avec succès !')
                else:
                    messages.error(request, 'Aucun exercice trouvé dans la réponse.')
            except json.JSONDecodeError:
                messages.error(request, 'Erreur: La réponse n\'est pas un JSON valide.')
        else:
            error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
            messages.error(request, f'Erreur API: {error_msg}')
            
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('ai_tools:exercise_generator')


@login_required
def submit_project_view(request):
    """Soumettre un projet à la galerie."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('ai_tools:gallery')
    
    if request.method == 'POST':
        # هنا هتضيف منطق حفظ المشروع
        messages.success(request, 'Projet soumis avec succès !')
        return redirect('ai_tools:gallery')
    
    return render(request, 'ai_tools/submit_project.html')


@login_required
def generate_lesson_view(request):
    """Générateur de leçons numériques avec IA."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    
    generated_lesson = None
    
    if request.method == 'POST':
        topic = request.POST.get('topic')
        level = request.POST.get('level')
        lesson_type = request.POST.get('lesson_type')
        duration = request.POST.get('duration')
        
        if not topic:
            messages.error(request, 'Veuillez entrer un thème pour la leçon.')
            return render(request, 'ai_tools/generate_lesson.html')
        
        try:
            # ✅ Appel à l'API Groq
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Crée une leçon complète sur le thème : "{topic}" pour le niveau {level}.
            Type de leçon : {lesson_type}.
            Durée estimée : {duration} minutes.
            
            Structure de la leçon :
            1. Objectifs pédagogiques
            2. Introduction (accroche)
            3. Corps de la leçon (contenu principal avec exemples)
            4. Exercices d'application (3 exercices)
            5. Résumé / Conclusion
            
            Réponds en français avec un format clair et structuré.
            """
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Tu es un professeur de français expert. Tu crées des leçons structurées et pédagogiques en français."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if response.status_code == 200:
                content = result['choices'][0]['message']['content']
                generated_lesson = {
                    'title': topic,
                    'level': level,
                    'type': lesson_type,
                    'duration': duration,
                    'content': content.replace('\n', '<br>')
                }
                request.session['generated_lesson'] = generated_lesson
                messages.success(request, f'✅ Leçon générée avec succès !')
            else:
                error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
                messages.error(request, f'Erreur API: {error_msg}')
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    if 'generated_lesson' in request.session:
        generated_lesson = request.session['generated_lesson']
    
    return render(request, 'ai_tools/generate_lesson.html', {'generated_lesson': generated_lesson})

@login_required
def generate_game_view(request):
    """Générateur de jeux éducatifs avec IA."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    
    generated_game = None
    
    if request.method == 'POST':
        theme = request.POST.get('theme')
        level = request.POST.get('level')
        game_type = request.POST.get('game_type')
        count = request.POST.get('count')
        
        if not theme:
            messages.error(request, 'Veuillez entrer un thème pour le jeu.')
            return render(request, 'ai_tools/generate_game.html')
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Crée un jeu éducatif de type {game_type} sur le thème "{theme}" pour le niveau {level}.
            Nombre de questions : {count}.
            
            Format :
            - Titre du jeu
            - Instructions
            - Questions avec réponses
            
            Réponds en français.
            """
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Tu es un créateur de jeux éducatifs. Tu crées des jeux amusants et pédagogiques."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if response.status_code == 200:
                content = result['choices'][0]['message']['content']
                generated_game = {
                    'theme': theme,
                    'level': level,
                    'type': game_type,
                    'count': count,
                    'content': content.replace('\n', '<br>')
                }
                request.session['generated_game'] = generated_game
                messages.success(request, f'✅ Jeu généré avec succès !')
            else:
                error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
                messages.error(request, f'Erreur API: {error_msg}')
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    if 'generated_game' in request.session:
        generated_game = request.session['generated_game']
    
    return render(request, 'ai_tools/generate_game.html', {'generated_game': generated_game})


@login_required
def generate_mindmap_view(request):
    """Générateur de cartes mentales avec IA."""
    if not request.user.is_teacher and not request.user.is_staff:
        messages.error(request, 'Cette fonctionnalité est réservée aux enseignants.')
        return redirect('accounts:dashboard')
    
    generated_mindmap = None
    
    if request.method == 'POST':
        topic = request.POST.get('topic')
        map_type = request.POST.get('map_type')
        detail = request.POST.get('detail')
        language = request.POST.get('language')
        
        if not topic:
            messages.error(request, 'Veuillez entrer un sujet pour la carte.')
            return render(request, 'ai_tools/generate_mindmap.html')
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""
            Crée une carte {map_type} sur le sujet "{topic}" en {language}.
            Niveau de détail : {detail}.
            
            Structure (uniquement les idées principales et sous-idées) :
            - Sujet central
            - 3 à 5 branches principales
            - Sous-branches pour chaque branche
            
            Réponds en français.
            """
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Tu es un expert en organisation d'idées. Tu crées des cartes mentales claires et structurées."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 800,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if response.status_code == 200:
                content = result['choices'][0]['message']['content']
                generated_mindmap = {
                    'topic': topic,
                    'type': map_type,
                    'detail': detail,
                    'language': language,
                    'content': content.replace('\n', '<br>')
                }
                request.session['generated_mindmap'] = generated_mindmap
                messages.success(request, f'✅ Carte générée avec succès !')
            else:
                error_msg = result.get('error', {}).get('message', 'Erreur inconnue')
                messages.error(request, f'Erreur API: {error_msg}')
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    if 'generated_mindmap' in request.session:
        generated_mindmap = request.session['generated_mindmap']
    
    return render(request, 'ai_tools/generate_mindmap.html', {'generated_mindmap': generated_mindmap})