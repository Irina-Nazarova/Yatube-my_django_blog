from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Проверяем, является ли запрос операцией чтения или операцией записи.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in SAFE_METHODS:
            return True
        return request.user == obj.author


class IsAuthenticatedGetPost(BasePermission):
    """
    Проверяем, является ли запрос операцией чтения или операцией записи.
    Переопределяем класс IsAuthenticatedOrReadOnly на методы GET и POST.
    """

    def has_object_permission(self, request, view, obj):

        if request.method in ("GET", "POST"):
            return True
        return request.user == obj.author
