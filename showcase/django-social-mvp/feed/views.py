from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Post, Comment

def feed_list(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please select an active persona to post.")
            return redirect('feed')
        
        content = request.POST.get('content', '').strip()
        code_snippet = request.POST.get('code_snippet', '').strip()
        language = request.POST.get('language', 'python').strip()
        tags = request.POST.get('tags', '').strip()

        if content:
            Post.objects.create(
                author=request.user,
                content=content,
                code_snippet=code_snippet,
                language=language,
                tags=tags
            )
            messages.success(request, "Engineering dispatch published.")
            return redirect('feed')

    # Efficient querying: select_related and prefetch_related to eliminate N+1 queries
    posts = Post.objects.select_related('author', 'author__profile')\
                        .prefetch_related('comments', 'comments__author', 'comments__author__profile', 'likes')\
                        .all()

    all_users = User.objects.select_related('profile').all()
    total_posts = Post.objects.count()
    total_comments = Comment.objects.count()

    return render(request, 'feed/feed.html', {
        'posts': posts,
        'all_users': all_users,
        'total_posts': total_posts,
        'total_comments': total_comments,
    })

@login_required(login_url='login')
@require_POST
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'liked': liked,
            'like_count': post.likes.count()
        })
    return redirect('feed')

@login_required(login_url='login')
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    content = request.POST.get('content', '').strip()
    if content:
        Comment.objects.create(
            post=post,
            author=request.user,
            content=content
        )
        messages.success(request, "Comment appended to thread.")
    return redirect('feed')
