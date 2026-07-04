from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.contrib.auth import views as auth_views  # ✅ أضف هذا السطر

def home_page(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('rosetta/', include('rosetta.urls')),  # ✅ أضف هذا السطر
    path('', home_page, name='home'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('courses/', include('apps.courses.urls', namespace='courses')),
    path('live/', include('apps.live_stream.urls', namespace='live_stream')),
    path('ai/', include('apps.ai_tools.urls', namespace='ai_tools')),
    path('ar/', include('apps.ar_content.urls', namespace='ar_content')),
    path('api/accounts/', include('apps.accounts.api_urls')),
    path('api/courses/', include('apps.courses.api_urls')),
    path('api/live/', include('apps.live_stream.api_urls')),
    path('api/ai/', include('apps.ai_tools.api_urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # Password Reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)