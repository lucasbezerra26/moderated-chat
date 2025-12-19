from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet

from app.accounts.models import User
from app.chat.models import Message, Room, RoomParticipant


class MessageService:
    """
    Service para gerenciar operação de mensagens.
    Responsável por criar mensagens em estado PENDING e buscar histórico.
    """

    @staticmethod
    async def create_message(room: Room, author: User, content: str) -> Message:
        """
        Cria uma mensagem em estado PENDING e dispara moderação assíncrona.

        Args:
            room: Sala onde a mensagem será enviada
            author: Usuário autor da mensagem
            content: Conteúdo da mensagem

        Returns:
            Message: Mensagem criada com status PENDING
        """
        message = await Message.objects.acreate(
            room=room, author=author, content=content, status=Message.Status.PENDING
        )

        from app.moderation.tasks import moderate_message_task

        moderate_message_task.delay(str(message.id))

        return message

    @staticmethod
    async def get_room_messages(room: Room, status: Optional[str] = None, limit: int = 50) -> QuerySet[Message]:
        """
        Busca mensagens de uma sala com filtros opcionais.

        Args:
            room: Sala para buscar mensagens
            status: Filtro opcional por status (PENDING/APPROVED/REJECTED)
            limit: Limite de mensagens a retornar

        Returns:
            QuerySet[Message]: QuerySet de mensagens
        """
        queryset = Message.objects.filter(room=room).select_related("author")

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")[:limit]


class RoomService:
    """Service para gerenciar operações de salas."""

    @staticmethod
    async def create_room(name: str, creator: User, is_private: bool = False) -> Room:
        """
        Cria uma nova sala de chat com o criador como ADMIN.

        Args:
            name: Nome da sala
            creator: Usuário criador (será ADMIN automaticamente)
            is_private: Se a sala é privada

        Returns:
            Room: Sala criada
        """
        async with transaction.atomic():
            room = await Room.objects.acreate(name=name, is_private=is_private)
            await RoomParticipant.objects.acreate(room=room, user=creator, role=RoomParticipant.Role.ADMIN)
            return room

    @staticmethod
    async def add_participant(room: Room, new_user: User, requester: Optional[User] = None) -> RoomParticipant:
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

            is_admin = await RoomParticipant.objects.filter(
                room=room, user=requester, role=RoomParticipant.Role.ADMIN
            ).aexists()

            if not is_admin:
                raise PermissionDenied("Apenas administradores podem adicionar membros em salas privadas.")

        participant, _ = await RoomParticipant.objects.aget_or_create(
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


class BroadcastService:
    """Serviço responsável por comunicação via WebSocket (Channel Layer)."""

    @staticmethod
    def broadcast_message_to_room(message: Message) -> None:
        """
        Envia mensagem aprovada para todos os participantes da sala.

        Args:
            message: Mensagem aprovada para broadcast
        """

        channel_layer = get_channel_layer()
        room_group_name = f"chat_{message.room.id}"

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": str(message.id),
                    "content": message.content,
                    "author": {
                        "id": str(message.author.id),
                        "name": message.author.name,
                        "email": message.author.email,
                    },
                    "status": message.status,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    @staticmethod
    def notify_author_rejection(message: Message, details: dict) -> None:
        """
        Notifica o autor que sua mensagem foi rejeitada via WebSocket privado.

        Args:
            message: Mensagem rejeitada
            details: Detalhes da rejeição
        """
        channel_layer = get_channel_layer()
        user_channel_name = f"user_{message.author.id}"

        async_to_sync(channel_layer.group_send)(
            user_channel_name,
            {
                "type": "message_rejected",
                "message": {
                    "id": str(message.id),
                    "content": message.content,
                    "reason": details.get("reason", "content_violation"),
                    "created_at": message.created_at.isoformat(),
                },
            },
        )
