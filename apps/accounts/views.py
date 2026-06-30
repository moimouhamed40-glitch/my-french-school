from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone

from .models import User, StudentProfile, TeacherProfile, Notification
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    StudentProfileForm, TeacherProfileForm,
)


def home_view(request):
    from apps.courses.models import Course
    featured_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:6]
    stats = {
        'total_students': User.objects.filter(role=User.Role.STUDENT).count(),
        'total_courses': Course.objects.filter(is_published=True).count(),
        'total_teachers': User.objects.filter(role=User.Role.TEACHER).count(),
    }
    return render(request, 'home.html', {
        'featured_courses': featured_courses,
        'stats': stats,
        'levels': Course.Level.choices,
    })


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    form = UserRegistrationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user)
        elif user.role == User.Role.TEACHER:
            TeacherProfile.objects.create(user=user)
        login(request, user)
        messages.success(request, 'Bienvenue sur la plateforme !')
        return redirect('accounts:dashboard')

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bonjour, {user.first_name or user.username} !')
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Identifiants invalides.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('accounts:login')


@login_required
def dashboard_view(request):
    user = request.user
    if user.is_staff or user.is_superuser:
        return admin_dashboard(request)
    elif hasattr(user, 'teacher_profile'):
        return teacher_dashboard(request)
    else:
        return student_dashboard(request)


def student_dashboard(request):
    user = request.user
    from apps.courses.models import Enrollment, ExerciseSubmission
    from apps.live_stream.models import LiveSession
    
    enrollments = Enrollment.objects.filter(student=user).select_related('course')[:5]
    recent_submissions = ExerciseSubmission.objects.filter(student=user).order_by('-submitted_at')[:5]
    upcoming_sessions = LiveSession.objects.filter(is_active=True).order_by('scheduled_at')[:3]
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]

    context = {
        'enrollments': enrollments,
        'recent_submissions': recent_submissions,
        'upcoming_sessions': upcoming_sessions,
        'profile': profile,
        'notifications': notifications,
        'unread_count': notifications.count(),
    }
    return render(request, 'accounts/dashboard_student.html', context)


def teacher_dashboard(request):
    user = request.user
    from apps.courses.models import Course
    from apps.live_stream.models import LiveSession
    
    my_courses = Course.objects.filter(teacher=user).annotate(
        student_count=Count('enrollments'),
    ).order_by('-created_at')
    my_sessions = LiveSession.objects.filter(host=user).order_by('-created_at')[:5]
    profile, _ = TeacherProfile.objects.get_or_create(user=user)

    context = {
        'my_courses': my_courses,
        'my_sessions': my_sessions,
        'profile': profile,
        'total_students': sum(c.student_count for c in my_courses),
    }
    return render(request, 'accounts/dashboard_teacher.html', context)


def admin_dashboard(request):
    from apps.courses.models import Course
    from apps.live_stream.models import LiveSession
    
    stats = {
        'users': User.objects.values('role').annotate(count=Count('id')),
        'total_courses': Course.objects.count(),
        'published_courses': Course.objects.filter(is_published=True).count(),
        'active_sessions': LiveSession.objects.filter(is_active=True).count(),
        'recent_users': User.objects.order_by('-date_joined')[:10],
    }
    return render(request, 'accounts/dashboard_admin.html', {'stats': stats})


@login_required
def profile_view(request):
    user = request.user
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profil mis à jour.')
        return redirect('accounts:profile')

    role_form = None
    if hasattr(user, 'student_profile'):
        profile = user.student_profile
        role_form = StudentProfileForm(request.POST or None, instance=profile)
    elif hasattr(user, 'teacher_profile'):
        profile = user.teacher_profile
        role_form = TeacherProfileForm(request.POST or None, instance=profile)

    if role_form and request.method == 'POST' and role_form.is_valid():
        role_form.save()
        messages.success(request, 'Profil mis à jour.')
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {'form': form, 'role_form': role_form})


@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'accounts/notifications.html', {'notifications': notifs})


@login_required
def user_list_view(request):
    if not request.user.is_staff:
        messages.error(request, 'Accès refusé.')
        return redirect('accounts:dashboard')

    users = User.objects.all().order_by('-date_joined')
    return render(request, 'accounts/user_list.html', {'users': users})