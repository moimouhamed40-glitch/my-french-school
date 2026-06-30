"""
courses/views.py

Course listing, detail, lesson player, exercise submission, forum, and library views.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    Course, Lesson, Exercise, ExerciseSubmission,
    Enrollment, CourseProgress, LiteraryText,
    ForumThread, ForumReply, Category,
)
from .forms import (
    CourseForm, LessonForm, ExerciseForm,
    ForumThreadForm, ForumReplyForm,
)
from apps.accounts.models import StudentProfile, Notification


# ─── PUBLIC VIEWS ─────────────────────────────────────────────────────────────

def course_list_view(request):
    """Browse all published courses, filterable by level and category."""
    courses = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    level_filter = request.GET.get('level', '')
    category_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '')

    if level_filter:
        courses = courses.filter(level=level_filter)
    if category_filter:
        courses = courses.filter(category__slug=category_filter)
    if search_q:
        courses = courses.filter(
            Q(title__icontains=search_q) | Q(description__icontains=search_q)
        )

    courses = courses.annotate(student_count=Count('enrollments'))
    categories = Category.objects.all()

    return render(request, 'courses/list.html', {
        'courses': courses,
        'categories': categories,
        'level_choices': Course.Level.choices,
        'current_level': level_filter,
        'current_category': category_filter,
        'search_q': search_q,
    })


def course_detail_view(request, slug):
    """Course detail page with enrollment CTA."""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    lessons = course.lessons.all()
    is_enrolled = False
    progress_pct = 0

    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(
            student=request.user, course=course
        ).exists()
        if is_enrolled:
            completed = CourseProgress.objects.filter(
                student=request.user, lesson__course=course
            ).count()
            total = lessons.count()
            progress_pct = int((completed / total * 100) if total else 0)

    return render(request, 'courses/detail.html', {
        'course': course,
        'lessons': lessons,
        'is_enrolled': is_enrolled,
        'progress_pct': progress_pct,
    })


@login_required
def enroll_view(request, slug):
    """Enroll a student in a course."""
    course = get_object_or_404(Course, slug=slug)
    
    # ✅ استخدم get_or_create بدلاً من create
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )
    
    if created:
        messages.success(request, f'Vous êtes inscrit au cours "{course.title}" !')
    else:
        messages.info(request, f'Vous êtes déjà inscrit à ce cours.')
    
    return redirect('courses:detail', slug=course.slug)

@login_required
def lesson_view(request, slug, lesson_id):
    """Lesson player view."""
    course = get_object_or_404(Course, slug=slug)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)

    # Enforce enrollment for non-free lessons
    if not lesson.is_free_preview and not request.user.is_teacher:
        enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
        if not enrolled:
            messages.warning(request, _('Inscrivez-vous au cours pour accéder à cette leçon.'))
            return redirect('courses:detail', slug=slug)

    # Mark lesson as completed
    CourseProgress.objects.get_or_create(student=request.user, lesson=lesson)

    exercises = lesson.exercises.all()
    submitted_ids = ExerciseSubmission.objects.filter(
        student=request.user,
        exercise__in=exercises,
    ).values_list('exercise_id', flat=True)

    next_lesson = Lesson.objects.filter(
        course=course, order__gt=lesson.order
    ).order_by('order').first()

    prev_lesson = Lesson.objects.filter(
        course=course, order__lt=lesson.order
    ).order_by('-order').first()

    return render(request, 'courses/lesson.html', {
        'course': course,
        'lesson': lesson,
        'exercises': exercises,
        'submitted_ids': list(submitted_ids),
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'all_lessons': course.lessons.all(),
    })


@login_required
@require_POST
def submit_exercise_view(request, exercise_id):
    """Handle exercise submission and auto-correction."""
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    data = json.loads(request.body)
    student_answer = data.get('answer')

    # Auto-correction logic
    is_correct = False
    score = 0
    feedback = ''

    correct = exercise.correct_answer

    if exercise.exercise_type == Exercise.ExerciseType.MCQ:
        is_correct = str(student_answer) == str(correct.get('choice'))
    elif exercise.exercise_type == Exercise.ExerciseType.FILL_BLANK:
        # Compare list of answers case-insensitively
        student_list = [a.strip().lower() for a in (student_answer or [])]
        correct_list = [a.strip().lower() for a in correct.get('answers', [])]
        is_correct = student_list == correct_list
    elif exercise.exercise_type == Exercise.ExerciseType.ORDER_SENTENCE:
        student_order = student_answer if isinstance(student_answer, list) else []
        is_correct = student_order == correct.get('order', [])
    elif exercise.exercise_type == Exercise.ExerciseType.FREE_TEXT:
        # Free text: saved for teacher review
        is_correct = None
        feedback = _('Votre réponse a été enregistrée pour correction par l\'enseignant.')

    if is_correct:
        score = exercise.points
        feedback = feedback or _('Bonne réponse ! 🎉')
    elif is_correct is False:
        feedback = feedback or (
            _('Réponse incorrecte. ') +
            (f"Explication : {exercise.explanation}" if exercise.explanation else '')
        )

    attempt = ExerciseSubmission.objects.filter(
        student=request.user, exercise=exercise
    ).count() + 1

    submission = ExerciseSubmission.objects.create(
        student=request.user,
        exercise=exercise,
        answer_data={'answer': student_answer},
        is_correct=bool(is_correct),
        score=score,
        feedback=str(feedback),
        attempt_number=attempt,
    )

    # Award points
    if is_correct and score:
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        profile.total_points += score
        profile.save()

    return JsonResponse({
        'is_correct': is_correct,
        'score': score,
        'feedback': str(feedback),
        'correct_answer': correct,
        'submission_id': submission.pk,
    })


# ─── TEACHER COURSE MANAGEMENT ────────────────────────────────────────────────

@login_required
def create_course_view(request):
    if not request.user.is_teacher and not request.user.is_platform_admin:
        messages.error(request, _('Accès refusé.'))
        return redirect('accounts:dashboard')

    form = CourseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        course = form.save(commit=False)
        course.teacher = request.user
        course.save()
        messages.success(request, _('Cours créé avec succès.'))
        return redirect('courses:edit', slug=course.slug)

    return render(request, 'courses/create.html', {'form': form})


@login_required
def edit_course_view(request, slug):
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if form.is_valid():
        form.save()
        messages.success(request, _('Cours mis à jour.'))
        return redirect('courses:edit', slug=slug)

    lessons = course.lessons.all()
    return render(request, 'courses/edit.html', {
        'form': form,
        'course': course,
        'lessons': lessons,
    })


@login_required
def add_lesson_view(request, slug):
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    form = LessonForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        lesson = form.save(commit=False)
        lesson.course = course
        lesson.order = course.lessons.count() + 1
        lesson.save()
        messages.success(request, _('Leçon ajoutée.'))
        return redirect('courses:edit', slug=slug)
    return render(request, 'courses/add_lesson.html', {'form': form, 'course': course})


# ─── LIBRARY ──────────────────────────────────────────────────────────────────

def literary_library_view(request):
    level_filter = request.GET.get('level', '')
    texts = LiteraryText.objects.all()
    if level_filter:
        texts = texts.filter(level=level_filter)
    return render(request, 'courses/library.html', {
        'texts': texts,
        'level_choices': Course.Level.choices,
        'current_level': level_filter,
    })


def literary_text_view(request, pk):
    text = get_object_or_404(LiteraryText, pk=pk)
    return render(request, 'courses/literary_text.html', {'text': text})


# ─── FORUM ────────────────────────────────────────────────────────────────────

@login_required
def forum_list_view(request, slug=None):
    if slug:
        course = get_object_or_404(Course, slug=slug)
        threads = ForumThread.objects.filter(course=course)
    else:
        course = None
        threads = ForumThread.objects.all()

    threads = threads.annotate(reply_count=Count('replies')).select_related('author')
    return render(request, 'courses/forum_list.html', {
        'threads': threads,
        'course': course,
    })


@login_required
def forum_thread_view(request, thread_id):
    thread = get_object_or_404(ForumThread, pk=thread_id)
    reply_form = ForumReplyForm(request.POST or None)

    if reply_form.is_valid():
        reply = reply_form.save(commit=False)
        reply.thread = thread
        reply.author = request.user
        reply.save()
        messages.success(request, _('Réponse publiée.'))
        return redirect('courses:forum_thread', thread_id=thread_id)

    return render(request, 'courses/forum_thread.html', {
        'thread': thread,
        'replies': thread.replies.select_related('author'),
        'reply_form': reply_form,
    })


@login_required
def create_thread_view(request, slug=None):
    course = get_object_or_404(Course, slug=slug) if slug else None
    form = ForumThreadForm(request.POST or None)
    if form.is_valid():
        thread = form.save(commit=False)
        thread.author = request.user
        thread.course = course
        thread.save()
        messages.success(request, _('Discussion créée.'))
        return redirect('courses:forum_thread', thread_id=thread.pk)
    return render(request, 'courses/create_thread.html', {'form': form, 'course': course})
