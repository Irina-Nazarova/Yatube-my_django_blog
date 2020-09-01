from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.views.decorators.cache import cache_page

from .models import Post, Group, Follow
from .forms import PostForm, CommentForm


User = get_user_model()


@cache_page(20)
def index(request):
    latest = Post.objects.all()
    paginator = Paginator(latest, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request, "index.html", {"page": page, "paginator": paginator}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    latest = group.posts.all()
    paginator = Paginator(latest, 3)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)

    return render(
        request,
        "group.html",
        {"group": group, "page": page, "paginator": paginator},
    )


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("index")
    return render(request, "new_post.html", {"form": form})


def profile(request, username):
    post_author = get_object_or_404(User, username=username)
    latest = post_author.posts.all()
    count = post_author.posts.count()
    paginator = Paginator(latest, 4)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    following = None
    if request.user.is_authenticated:
        following = post_author.following.filter(user=request.user)
    return render(
        request,
        "profile.html",
        {
            "page": page,
            "paginator": paginator,
            "post_author": post_author,
            "count": count,
            "follower_count": post_author.following.count(),
            "following_count": post_author.follower.count(),
            "following": following,
        },
    )


def post_view(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    count = Post.objects.filter(author=post.author).count()
    comments = post.comments.all()
    form = CommentForm()
    return render(
        request,
        "post.html",
        {
            "count": count,
            "post_author": post.author,
            "post": post,
            "form": form,
            "comments": comments,
            "follower_count": post.author.following.count(),
            "following_count": post.author.follower.count(),
        },
    )


def post_edit(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    if request.user == post.author:
        form = PostForm(
            request.POST or None, files=request.FILES or None, instance=post
        )
        if form.is_valid():
            form.save()
            return redirect("post", username=username, post_id=post_id)
        context = {
            "form": form,
            "post": post,
            "can_edit": True,
        }
        return render(request, "new_post.html", context)
    else:
        return redirect(request, "index.html")


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)
    form = CommentForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()
        return redirect("post", username=username, post_id=post_id)
    return render(
        request,
        "post.html",
        {
            "post": post,
            "post_author": post.author,
            "form": form,
            "comments": post.comments.all(),
            "follower_count": post.author.following.count(),
            "following_count": post.author.follower.count(),
        },
    )


# вывод постов авторов, на которых подписан текущий пользователь.
@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(
        request, "follow.html", {"page": page, "paginator": paginator,}
    )


# подписка на интересного автора
@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect("profile", username=username)


# отписка от надоевшего графомана
@login_required
def profile_unfollow(request, username):
    profile_to_unfollow = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user).filter(
        author=profile_to_unfollow
    ).delete()
    return redirect("profile", username=username)
