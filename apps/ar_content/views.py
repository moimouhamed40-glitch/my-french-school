from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def ar_home_view(request):
    return render(request, 'ar_content/home.html')