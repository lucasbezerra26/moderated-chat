from typing import Optional

from django.core.exceptions import PermissionDenied

from app.accounts.models import User
from app.chat.models import Room, RoomParticipant


class RoomService:
    """Service para gerenciar operações de salas."""

    @staticmethod
    def create_room(name: str, creator: User, is_private: bool = False) -> Room:
        """
        Cria uma nova sala de chat com o criador como ADMIN.

        Args:
            name: Nome da sala
            creator: Usuário criador (será ADMIN automaticamente)
            is_private: Se a sala é privada

        Returns:
            Room: Sala criada
        """
        room = Room.objects.create(name=name, is_private=is_private)
        RoomParticipant.objects.create(room=room, user=creator, role=RoomParticipant.Role.ADMIN)
        return room

    @staticmethod
    def add_participant(room: Room, new_user: User, requester: Optional[User] = None) -> RoomParticipant:
        """
        Adiciona um participante à sala com validação de permissões.

        Em salas privadas, apenas ADMINs podem adicionar novos membros.

        Args:
            room: Sala para adicionar participante
            new_user: Usuário a ser adicionado
            requester: Usuário solicitante (obrigatório para salas privadas)

        Returns:
            RoomParticipant: Participação criada

        Raises:
            PermissionDenied: Se requester não é ADMIN em sala privada
        """
        if room.is_private:
            if not requester:
                raise PermissionDenied("Requester é obrigatório para salas privadas.")

            is_admin = RoomParticipant.objects.filter(
                room=room, user=requester, role=RoomParticipant.Role.ADMIN
            ).exists()

            if not is_admin:
                raise PermissionDenied("Apenas administradores podem adicionar membros em salas privadas.")

        participant, _ = RoomParticipant.objects.get_or_create(
            room=room, user=new_user, defaults={"role": RoomParticipant.Role.MEMBER}
        )
        return participant

    @staticmethod
    async def remove_participant(room: Room, user_to_remove: User, requester: Optional[User] = None) -> None:
        """
        Remove um participante da sala com validação de permissões.

        Em salas privadas, apenas ADMINs podem remover membros.

        Args:
            room: Sala para remover participante
            user_to_remove: Usuário a ser removido
            requester: Usuário solicitante (obrigatório para salas privadas)

        Raises:
            PermissionDenied: Se requester não é ADMIN em sala privada
        """
        if room.is_private:
            if not requester:
                raise PermissionDenied("Requester é obrigatório para salas privadas.")

            is_admin = await RoomParticipant.objects.filter(
                room=room, user=requester, role=RoomParticipant.Role.ADMIN
            ).aexists()

            if not is_admin:
                raise PermissionDenied("Apenas administradores podem remover membros em salas privadas.")

        await RoomParticipant.objects.filter(room=room, user=user_to_remove).adelete()
