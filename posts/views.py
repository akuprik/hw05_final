from django.core.paginator import Paginator
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import User, Post, Group, Comment, Follow
from .forms import CommentForm, PostForm


def is_not_folower(user, author):
    if user.is_authenticated:
        author = get_object_or_404(User, username=author)
        return Follow.objects.filter(user=user).filter(author=author).count() == 0
    return True


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.
    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator, "post_count_in_base": post_list.count}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    paginator = Paginator(group.posts.all(), 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"group": group, "page": page, 'paginator': paginator})


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            user = get_user(request)
            post = Post(group=form.cleaned_data['group'],
                        text=form.cleaned_data['text'],
                        author=user,
                        image=form.cleaned_data['image']
                        )
            post.save()
            return redirect(reverse('index'))
    else:
        form = PostForm()
    return render(request, 'new_post.html', {'form': form})


def profile(request, username):
    user = get_object_or_404(User, username=username)
    paginator = Paginator(user.posts.all(), 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'profile.html',
                  {"profile_user": user,
                   'post_count': paginator.count,
                   'page': page,
                   'paginator': paginator,
                   'following': not is_not_folower(request.user, username),
                   }
                  )


def post_view(request, username, post_id):
    user = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id)
    post_count = user.posts.all().count
    comments = post.comments.all()
    commentform = CommentForm()
    return render(request, 'post.html',
                  {"profile_user": user,
                   'post_count': post_count,
                   'post': post,
                   'comments': comments,
                   'commentform': commentform,
                   }
                  )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if request.method == 'POST':
        if form.is_valid():
            post.save()
            return redirect(reverse('post', kwargs={'username': post.author, 'post_id': post_id}))

    if post.author == get_user(request):
        return render(request, 'new_post.html', {'form': form, 'post': post})

    return redirect(reverse('post', kwargs={'username': post.author.username, 'post_id': post_id}))


@login_required
def add_comment(request, username, post_id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            user = get_user(request)
            comment = Comment(author=user,
                              post=get_object_or_404(Post, pk=post_id),
                              text=form.cleaned_data['text'],
                              )
            comment.save()
    return redirect(reverse('post', kwargs={'username': username, 'post_id': post_id}))


@login_required
def follow_index(request):
    # информация о текущем пользователе доступна в переменной request.user
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.
    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(
        request,
        'follow.html',
        {'page': page, 'paginator': paginator, "post_count_in_base": post_list.count}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user.username != username:  # не подписываем сомого на себя
        if is_not_folower(request.user, username):
            follow = Follow(user=request.user, author=author)
            follow.save()
    return redirect(reverse('profile', kwargs={'username': username}))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user).filter(author=author).delete()
    return redirect(reverse('profile', kwargs={'username': username}))
