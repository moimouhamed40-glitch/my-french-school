from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import LiveSession


def live_list_view(request):
    sessions = LiveSession.objects.filter(is_active=True).order_by('scheduled_at')
    return render(request, 'live_stream/list.html', {'sessions': sessions})


def live_detail_view(request, pk):
    session = get_object_or_404(LiveSession, pk=pk)
    return render(request, 'live_stream/detail.html', {'session': session})


@login_required
def create_live_view(request):
    if not request.user.is_teacher:
        messages.error(request, _('Only teachers can create live sessions.'))
        return redirect('live_stream:list')
    
    if request.method == 'POST':
        messages.success(request, _('Live session created successfully!'))
        return redirect('live_stream:list')
    
    return render(request, 'live_stream/create.html')