from typing import Optional
from django.db.models import QuerySet
from app.chat.models import Room, Message
from app.accounts.models import User


class MessageService:
    """
    Service para gerenciar operação de mensagens.
    Responsável por criar mensagens em estado PENDING e buscar histórico.
    """

    @staticmethod
    async def create_message(
        room: Room,
        author: User,
        content: str
    ) -> Message:
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
            room=room,
            author=author,
            content=content,
            status=Message.Status.PENDING
        )

        from app.moderation.tasks import moderate_message_task
        moderate_message_task.delay(str(message.id))

        return message

    @staticmethod
    async def get_room_messages(
        room: Room,
        status: Optional[str] = None,
        limit: int = 50
    ) -> QuerySet[Message]:
        """
        Busca mensagens de uma sala com filtros opcionais.

        Args:
            room: Sala para buscar mensagens
            status: Filtro opcional por status (PENDING/APPROVED/REJECTED)
            limit: Limite de mensagens a retornar

        Returns:
            QuerySet[Message]: QuerySet de mensagens
        """
        queryset = Message.objects.filter(room=room).select_related('author')

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')[:limit]


class RoomService:
    """
    Service para gerenciar operações de salas.
    """

    @staticmethod
    async def create_room(
        name: str,
        is_private: bool = False,
        creator: Optional[User] = None
    ) -> Room:
        """
        Cria uma nova sala de chat.

        Args:
            name: Nome da sala
            is_private: Se a sala é privada
            creator: Usuário criador (será adicionado automaticamente)

        Returns:
            Room: Sala criada
        """
        room = await Room.objects.acreate(
            name=name,
            is_private=is_private
        )

        if creator:
            await room.participants.aadd(creator)

        return room

    @staticmethod
    async def add_participant(room: Room, user: User) -> None:
        """
        Adiciona um participante à sala.

        Args:
            room: Sala para adicionar participante
            user: Usuário a ser adicionado
        """
        await room.participants.aadd(user)

    @staticmethod
    async def remove_participant(room: Room, user: User) -> None:
        """
        Remove um participante da sala.

        Args:
            room: Sala para remover participante
            user: Usuário a ser removido
        """
        await room.participants.aremove(user)

