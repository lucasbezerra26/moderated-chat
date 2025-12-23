from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from app.chat.models import Message


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
