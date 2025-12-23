from rest_framework.permissions import BasePermission

from app.chat.models import RoomParticipant


class IsRoomParticipant(BasePermission):
    """Verifica se o usuário é participante da sala."""

    def has_object_permission(self, request, view, obj) -> bool:
        return RoomParticipant.objects.filter(room=obj, user=request.user).exists()


class IsRoomParticipantOrPublic(BasePermission):
    """
    Verifica se o usuário pode acessar a sala.

    Permite acesso se:
    - Sala é pública (qualquer usuário autenticado)
    - Sala é privada E usuário é participante
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if not obj.is_private:
            return True
        return RoomParticipant.objects.filter(room=obj, user=request.user).exists()


class IsRoomAdmin(BasePermission):
    """Verifica se o usuário é administrador da sala."""

    def has_object_permission(self, request, view, obj) -> bool:
        return RoomParticipant.objects.filter(room=obj, user=request.user, role=RoomParticipant.Role.ADMIN).exists()
