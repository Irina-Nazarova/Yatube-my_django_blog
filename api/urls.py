from django.urls import path, include
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import PostViewSet, CommentViewSet, FollowViewSet, GroupViewSet

v1_router = DefaultRouter()
v1_router.register("posts", PostViewSet, basename="posts")
v1_router.register(
    r"posts/(?P<post_id>\d+)/comments", CommentViewSet, basename="post_id"
)
v1_router.register("follow", FollowViewSet, basename="follow")
v1_router.register("group", GroupViewSet, basename="group")

urlpatterns = [
    path("v1/", include(v1_router.urls),),
    path("v1/api-token-auth/", views.obtain_auth_token),
    path("v1/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "v1/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
]
