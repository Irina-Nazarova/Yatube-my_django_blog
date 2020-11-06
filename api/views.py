from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import viewsets, generics
from rest_framework import filters
from rest_framework.viewsets import ViewSetMixin

from api.serializers import (
    PostSerializer,
    CommentSerializer,
    GroupSerializer,
    FollowSerializer,
)
from api.permissions import IsOwnerOrReadOnly, IsAuthenticatedGetPost
from posts.models import Post, Group, Follow


class PostViewSet(viewsets.ModelViewSet):
    """
    Выводим все посты. Делаем проверку на аутентификацию.
    Используем класс ModelViewSet, чтобы получить полный набор
    операций чтения и записи по умолчанию.
    """

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "group",
    ]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    """
    Выводим комментарий поста по ключу. Делаем проверку на аутентификацию.
    Используем класс ModelViewSet, чтобы получить полный набор операций
    чтения и записи по умолчанию.
    """

    serializer_class = CommentSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        serializer.save(author=self.request.user, post=post)

    def get_queryset(self):
        post = get_object_or_404(Post, pk=self.kwargs["post_id"])
        return post.comments


class FollowViewSet(ViewSetMixin, generics.ListCreateAPIView):
    """
    Выводим все подписки. Делаем проверку на аутентификацию.
    Используем класс ListCreateAPIView для
    определения поведения GET и POST.
    """

    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = (IsAuthenticatedGetPost,)
    filter_backends = [filters.SearchFilter]
    search_fields = ("=user__username", "=following__username")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class GroupViewSet(ViewSetMixin, generics.ListCreateAPIView):
    """
    Выводим все группы. Делаем проверку на аутентификацию.
    Используем класс ListCreateAPIView для
    определения поведения GET и POST.
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (IsAuthenticatedGetPost,)
