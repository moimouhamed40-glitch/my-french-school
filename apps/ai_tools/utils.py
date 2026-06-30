"""
ai_tools/utils.py

AI utilities:
  - generate_exercises()       → OpenAI GPT exercise generation
  - correct_grammar_spacy()    → spaCy French grammar correction
  - get_chatbot_response()     → OpenAI conversational chatbot
  - build_exercise_prompt()    → Prompt builder helper
"""

import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── OPENAI CLIENT ────────────────────────────────────────────────────────────

def _get_openai_client():
    try:
        from openai import OpenAI
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        return None


# ─── EXERCISE GENERATION ──────────────────────────────────────────────────────

EXERCISE_SYSTEM_PROMPT = """Tu es un expert en didactique du français langue étrangère (FLE).
Tu génères des exercices pédagogiques précis, variés et adaptés au niveau CECRL indiqué.
Tu réponds UNIQUEMENT en JSON valide, sans aucun texte supplémentaire.
"""

EXERCISE_TYPE_INSTRUCTIONS = {
    'mcq': "QCM avec 4 choix (A, B, C, D) dont un seul correct.",
    'fill_blank': "Compléter les trous : une phrase avec [___] à la place du mot manquant.",
    'order_sentence': "Remettre les mots dans l'ordre pour former une phrase correcte.",
    'free_text': "Question ouverte avec une réponse modèle.",
}


def build_exercise_prompt(grammar_rule: str, level: str, exercise_type: str, count: int = 10) -> str:
    type_instruction = EXERCISE_TYPE_INSTRUCTIONS.get(exercise_type, "Exercice varié.")
    return f"""
Génère exactement {count} exercices de français de niveau {level} sur la règle grammaticale suivante :
« {grammar_rule} »

Type d'exercice : {type_instruction}

Réponds avec un tableau JSON de {count} objets ayant cette structure exacte :
{{
  "exercises": [
    {{
      "title": "Exercice 1 – {grammar_rule}",
      "question": "...",
      "content_data": {{...}},
      "correct_answer": {{...}},
      "explanation": "..."
    }}
  ]
}}

Règles de structure selon le type :

Pour "mcq":
  content_data: {{"choices": {{"A": "...", "B": "...", "C": "...", "D": "..."}}}}
  correct_answer: {{"choice": "A"}}

Pour "fill_blank":
  question contient [___] pour le(s) mot(s) manquant(s)
  content_data: {{"hint": "indice facultatif"}}
  correct_answer: {{"answers": ["mot1", "mot2"]}}

Pour "order_sentence":
  content_data: {{"words": ["mot1", "mot2", ...]}} (mélangés)
  correct_answer: {{"order": ["mot1", "mot2", ...]}} (ordre correct)

Assure-toi que les exercices sont progressifs, variés et pédagogiquement solides.
"""


def generate_exercises(
    grammar_rule: str,
    level: str,
    exercise_type: str,
    count: int = 10,
    course=None,
    teacher=None,
) -> dict:
    """
    Generate exercises using OpenAI GPT.
    Returns: {success, exercises, raw_response, tokens_used, error}
    """
    client = _get_openai_client()
    if not client:
        return {'success': False, 'error': 'OpenAI client unavailable', 'exercises': []}

    prompt = build_exercise_prompt(grammar_rule, level, exercise_type, count)

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': EXERCISE_SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={'type': 'json_object'},
        )

        raw = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        data = json.loads(raw)
        exercises_data = data.get('exercises', [])

        # Save to DB
        from apps.ai_tools.models import AIExerciseGeneration
        from apps.courses.models import Exercise

        log_entry = None
        if teacher:
            log_entry = AIExerciseGeneration.objects.create(
                teacher=teacher,
                grammar_rule=grammar_rule,
                level=level,
                exercise_type=exercise_type,
                prompt_used=prompt,
                raw_response=raw,
                exercises_created=len(exercises_data),
                linked_course=course,
                tokens_used=tokens_used,
            )

        # Optionally persist exercises to DB
        created_exercises = []
        if course and exercises_data:
            for i, ex_data in enumerate(exercises_data):
                ex = Exercise.objects.create(
                    course=course,
                    title=ex_data.get('title', f'Exercice {i+1}'),
                    exercise_type=exercise_type,
                    question=ex_data.get('question', ''),
                    content_data=ex_data.get('content_data', {}),
                    correct_answer=ex_data.get('correct_answer', {}),
                    explanation=ex_data.get('explanation', ''),
                    points=10,
                    order=i + 1,
                    ai_generated=True,
                )
                created_exercises.append(ex.pk)

        return {
            'success': True,
            'exercises': exercises_data,
            'db_exercise_ids': created_exercises,
            'tokens_used': tokens_used,
            'raw_response': raw,
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in AI response: {e}")
        return {'success': False, 'error': 'Invalid JSON from AI', 'exercises': []}
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return {'success': False, 'error': str(e), 'exercises': []}


# ─── GRAMMAR CORRECTION (spaCy) ───────────────────────────────────────────────

def correct_grammar_spacy(text: str) -> dict:
    """
    Perform grammar analysis using spaCy French model.
    Returns: {corrected_text, errors, error_count, suggestions}

    Install French model: python -m spacy download fr_core_news_md
    """
    try:
        import spacy

        try:
            nlp = spacy.load('fr_core_news_md')
        except OSError:
            nlp = spacy.load('fr_core_news_sm')

        doc = nlp(text)
        errors = []
        suggestions = []

        # Check for common French grammar issues
        for i, token in enumerate(doc):
            # Subject-verb agreement (simplified detection)
            if token.dep_ == 'nsubj' and token.head.pos_ == 'VERB':
                subj = token
                verb = token.head
                # Flag potential agreement issues (heuristic)
                if subj.morph.get('Number') and verb.morph.get('Number'):
                    subj_num = subj.morph.get('Number')[0]
                    verb_num = verb.morph.get('Number')[0] if verb.morph.get('Number') else None
                    if verb_num and subj_num != verb_num:
                        errors.append({
                            'type': 'accord_sujet_verbe',
                            'token': verb.text,
                            'position': verb.idx,
                            'message': f"Accord sujet-verbe possible entre « {subj.text} » et « {verb.text} »",
                        })

            # Detect repeated words
            if i > 0 and token.text.lower() == doc[i-1].text.lower() and token.is_alpha:
                errors.append({
                    'type': 'mot_répété',
                    'token': token.text,
                    'position': token.idx,
                    'message': f"Mot répété : « {token.text} »",
                })

        # Punctuation checks (simple)
        sentences = list(doc.sents)
        for sent in sentences:
            if not sent.text.strip().endswith(('.', '!', '?', ':', ';', '…')):
                errors.append({
                    'type': 'ponctuation',
                    'token': sent[-1].text,
                    'position': sent[-1].idx,
                    'message': f"Phrase sans ponctuation finale : « ...{sent[-1].text} »",
                })

        # Save to DB
        from apps.ai_tools.models import GrammarCorrectionLog
        # Note: save_grammar_log is called from the view with the user

        return {
            'original_text': text,
            'corrected_text': text,  # spaCy detects but doesn't auto-correct
            'errors': errors,
            'error_count': len(errors),
            'suggestions': suggestions,
            'tokens': [
                {
                    'text': t.text,
                    'lemma': t.lemma_,
                    'pos': t.pos_,
                    'dep': t.dep_,
                    'is_stop': t.is_stop,
                }
                for t in doc if t.is_alpha
            ],
        }

    except ImportError:
        return {
            'original_text': text,
            'corrected_text': text,
            'errors': [],
            'error_count': 0,
            'suggestions': ['spaCy non installé. Exécutez: pip install spacy && python -m spacy download fr_core_news_md'],
        }
    except Exception as e:
        logger.error(f"spaCy error: {e}")
        return {
            'original_text': text,
            'corrected_text': text,
            'errors': [],
            'error_count': 0,
            'suggestions': [f'Erreur: {str(e)}'],
        }


# ─── EDUCATIONAL CHATBOT ──────────────────────────────────────────────────────

CHATBOT_SYSTEM_PROMPT = """Tu es un assistant pédagogique spécialisé en français langue étrangère (FLE).
Tu aides les élèves à apprendre le français (niveaux A1, A2, B1).
Tes réponses sont :
- Claires, bienveillantes et encourageantes
- Adaptées au niveau de l'élève
- Toujours en français (sauf si l'élève pose une question en arabe, tu réponds en arabe + français)
- Pédagogiques : tu expliques les règles avec des exemples
- Tu corriges les fautes de façon constructive, sans décourager

Tu peux aider avec : vocabulaire, grammaire, conjugaison, prononciation, textes, exercices.
"""


def get_chatbot_response(messages_history: list, user_message: str, user_level: str = 'A1') -> dict:
    """
    Get a response from the educational chatbot.
    messages_history: list of {'role': 'user'|'assistant', 'content': str}
    Returns: {success, response, tokens_used, error}
    """
    client = _get_openai_client()
    if not client:
        return {'success': False, 'error': 'OpenAI unavailable', 'response': ''}

    system_with_level = CHATBOT_SYSTEM_PROMPT + f"\nNiveau actuel de l'élève : {user_level}."

    api_messages = [
        {'role': 'system', 'content': system_with_level},
        *messages_history[-10:],  # Keep last 10 messages for context
        {'role': 'user', 'content': user_message},
    ]

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=api_messages,
            temperature=0.6,
            max_tokens=800,
        )

        reply = response.choices[0].message.content
        tokens = response.usage.total_tokens

        return {
            'success': True,
            'response': reply,
            'tokens_used': tokens,
        }

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return {'success': False, 'error': str(e), 'response': ''}


# ─── PROMPT TEMPLATE RENDERER ─────────────────────────────────────────────────

def render_ai_template(template_text: str, variables: dict) -> str:
    """Replace {variable} placeholders in a template with actual values."""
    result = template_text
    for key, value in variables.items():
        result = result.replace(f'{{{key}}}', str(value))
    return result
