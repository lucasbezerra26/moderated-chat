from unittest.mock import patch

import pytest
from model_bakery import baker

from app.accounts.models import User
from app.chat.models import Message, Room
from app.moderation.models import ModerationLog
from app.moderation.tasks import moderate_message_task


@pytest.mark.django_db
class TestModerationTask:
    def test_moderate_message_task_approved(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="Safe message", status=Message.Status.PENDING)

        with patch("app.chat.services.BroadcastService.broadcast_message_to_room") as mock_broadcast:
            result = moderate_message_task(str(message.id))

            message.refresh_from_db()
            assert message.status == Message.Status.APPROVED
            assert result["status"] == "success"
            assert result["verdict"] == Message.Status.APPROVED
            mock_broadcast.assert_called_once()
            assert ModerationLog.objects.filter(message=message).exists()

    def test_moderate_message_task_rejected(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="idiota", status=Message.Status.PENDING)

        with patch("app.chat.services.BroadcastService.notify_author_rejection") as mock_notify:
            result = moderate_message_task(str(message.id))

            message.refresh_from_db()
            assert message.status == Message.Status.REJECTED
            assert result["verdict"] == Message.Status.REJECTED
            mock_notify.assert_called_once()

    def test_moderate_message_task_idempotency(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="Safe", status=Message.Status.APPROVED)

        result = moderate_message_task(str(message.id))
        assert result["status"] == "skipped"
        assert "already" in result["reason"]
