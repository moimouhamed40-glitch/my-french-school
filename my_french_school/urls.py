from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

def home_page(request):
    return render(request, 'home.html')

urlpatterns = [
    path('admin/', admin.site.urls),
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)