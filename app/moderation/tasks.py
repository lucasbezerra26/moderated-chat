import uuid

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.db import transaction

from app.chat.models import Message
from app.moderation.models import ModerationLog
from app.moderation.services import ModerationService


@shared_task(
    bind=True, max_retries=3, default_retry_delay=5, autoretry_for=(Exception,), retry_backoff=True, task_time_limit=30
)
def moderate_message_task(self, message_id: str) -> dict:
    """
    Task moderar uma mensagem.

    Usa Pessimistic Locking (select_for_update) para garantir idempotência forte.
    Evita race conditions quando múltiplas tasks tentam processar a mesma mensagem.

    Args:
        message_id: UUID da mensagem a ser moderada

    Returns:
        dict: Resultado da moderação com status e detalhes
    """
    try:
        message_uuid = uuid.UUID(message_id)

        with transaction.atomic():
            message = (
                Message.objects.select_for_update(nowait=False).select_related("room", "author").get(id=message_uuid)
            )

            if message.status != Message.Status.PENDING:
                return {"status": "skipped", "reason": f"Message already {message.status}", "message_id": message_id}

            moderation_result = ModerationService.moderate(message.content)

            ModerationLog.objects.create(
                message=message,
                provider=moderation_result["provider"],
                verdict=moderation_result["verdict"],
                score=moderation_result.get("score"),
                raw_payload=moderation_result,
            )

            message.status = moderation_result["verdict"]
            message.save(update_fields=["status", "updated_at"])

        if message.status == Message.Status.APPROVED:
            _broadcast_message_to_room(message)
        elif message.status == Message.Status.REJECTED:
            _notify_author_rejection(message, moderation_result.get("details", {}))

        return {
            "status": "success",
            "verdict": message.status,
            "message_id": message_id,
            "provider": moderation_result["provider"],
        }

    except Message.DoesNotExist:
        return {"status": "error", "reason": "Message not found", "message_id": message_id}
    except Exception as exc:
        raise self.retry(exc=exc)


def _broadcast_message_to_room(message: Message) -> None:
    """
    Envia mensagem aprovada para todos os participantes da sala via WebSocket.

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
                "author": {"id": str(message.author.id), "name": message.author.name, "email": message.author.email},
                "status": message.status,
                "created_at": message.created_at.isoformat(),
            },
        },
    )


def _notify_author_rejection(message: Message, details: dict) -> None:
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
