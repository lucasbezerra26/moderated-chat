import uuid

import structlog
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import transaction

from app.chat.models import Message
from app.chat.services.broadcast_service import BroadcastService
from app.moderation.models import ModerationLog
from app.moderation.services.moderator import ModerationService

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    task_time_limit=300,
    task_soft_time_limit=290,
    acks_late=True,
)
def moderate_message_task(self, message_id: str) -> dict:
    """
    Task para moderar uma mensagem com garantia de consistência.

    Combina 'acks_late=True' (Garantia de Entrega) com 'select_for_update'
    (Garantia de Idempotência) para evitar processamento duplicado em caso de
    retries ou falhas de worker.
    """
    log = logger.bind(message_id=message_id, task_id=self.request.id)
    try:
        message_uuid = uuid.UUID(message_id)

        with transaction.atomic():
            message = (
                Message.objects.select_for_update(nowait=False).select_related("room", "author").get(id=message_uuid)
            )

            if message.status != Message.Status.PENDING:
                log.info("moderation_skipped", current_status=message.status)
                return {"status": "skipped", "reason": f"Message already {message.status}", "message_id": message_id}

            log.info("starting_moderation", content=message.content[:50])
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
            log.info("message_approved")
            BroadcastService.broadcast_message_to_room(message)
        elif message.status == Message.Status.REJECTED:
            log.info("message_rejected", reason=moderation_result.get("details", {}).get("reason"))
            BroadcastService.notify_author_rejection(message, moderation_result.get("details", {}))

        return {
            "status": "success",
            "verdict": message.status,
            "message_id": message_id,
            "provider": moderation_result["provider"],
        }

    except Message.DoesNotExist:
        log.error("message_not_found")
        return {"status": "error", "reason": "Message not found", "message_id": message_id}
    except SoftTimeLimitExceeded:
        logger.warning("moderation_timeout_soft", message_id=message_id, retry=self.request.retries)
        raise self.retry(exc=SoftTimeLimitExceeded("Timeout de moderação atingido"))
    except Exception as exc:
        log.exception("moderation_task_failed", retry_count=self.request.retries)
        raise self.retry(exc=exc)
