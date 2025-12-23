from app.accounts.models import User
from app.chat.models import Message, Room


class MessageService:
    """
    Service para gerenciar operação de mensagens.
    Responsável por criar mensagens em estado PENDING
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
