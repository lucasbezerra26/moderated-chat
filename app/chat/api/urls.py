from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.chat.api.views import RoomViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet, basename="room")

urlpatterns = [
    path("", include(router.urls)),
]
