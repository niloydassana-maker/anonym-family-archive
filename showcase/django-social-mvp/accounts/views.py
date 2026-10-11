from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import Profile

def profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=target_user)
    posts = target_user.posts.all().order_by('-created_at')
    return render(request, 'accounts/profile.html', {
        'target_user': target_user,
        'profile': profile,
        'posts': posts,
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('feed')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('feed')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def switch_user(request, user_id):
    """Convenience helper for live demo walkthrough to switch perspective seamlessly."""
    target_user = get_object_or_404(User, id=user_id)
    login(request, target_user)
    messages.success(request, f"Active perspective switched to: {target_user.get_full_name() or target_user.username}")
    return redirect('feed')
