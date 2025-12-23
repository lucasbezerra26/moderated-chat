from unittest.mock import patch

import pytest
from model_bakery import baker

from app.accounts.models import User
from app.chat.models import Message, Room
from app.moderation.models import ModerationLog
from app.moderation.tasks import moderate_message_task


@pytest.mark.django_db
@pytest.mark.integration
class TestModerationTask:
    def test_moderate_message_task_approved_local(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="Safe message", status=Message.Status.PENDING)

        with patch("app.chat.services.BroadcastService.broadcast_message_to_room") as mock_broadcast:
            result = moderate_message_task(str(message.id))

            message.refresh_from_db()
            assert message.status == Message.Status.APPROVED
            assert result["status"] == "success"
            assert result["verdict"] == Message.Status.APPROVED
            assert result["provider"] == "local_dictionary"
            mock_broadcast.assert_called_once()
            assert ModerationLog.objects.filter(message=message).exists()

    def test_moderate_message_task_rejected_local(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="idiota", status=Message.Status.PENDING)

        with patch("app.chat.services.BroadcastService.notify_author_rejection") as mock_notify:
            result = moderate_message_task(str(message.id))

            message.refresh_from_db()
            assert message.status == Message.Status.REJECTED
            assert result["verdict"] == Message.Status.REJECTED
            assert result["provider"] == "local_dictionary"
            mock_notify.assert_called_once()

            call_args = mock_notify.call_args
            assert call_args[0][0] == message
            assert "reason" in call_args[0][1]

    def test_moderate_message_task_approved_gemini(self, db, settings):
        settings.MODERATION_PROVIDER = "gemini"

        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="Safe message", status=Message.Status.PENDING)

        with patch("app.moderation.services.gemini._analyze_text_with_gemini") as mock_gemini:
            mock_gemini.return_value = (True, "")

            with patch("app.chat.services.BroadcastService.broadcast_message_to_room") as mock_broadcast:
                result = moderate_message_task(str(message.id))

                message.refresh_from_db()
                assert message.status == Message.Status.APPROVED
                assert result["status"] == "success"
                assert result["verdict"] == Message.Status.APPROVED
                assert result["provider"] == "google_gemini"
                mock_broadcast.assert_called_once()
                assert ModerationLog.objects.filter(message=message).exists()

    def test_moderate_message_task_rejected_gemini(self, db, settings):
        settings.MODERATION_PROVIDER = "gemini"

        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(
            Message, room=room, author=user, content="Mensagem ofensiva", status=Message.Status.PENDING
        )

        with patch("app.moderation.services.gemini._analyze_text_with_gemini") as mock_gemini:
            mock_gemini.return_value = (False, "Conteúdo contém discurso de ódio")

            with patch("app.chat.services.BroadcastService.notify_author_rejection") as mock_notify:
                result = moderate_message_task(str(message.id))

                message.refresh_from_db()
                assert message.status == Message.Status.REJECTED
                assert result["verdict"] == Message.Status.REJECTED
                assert result["provider"] == "google_gemini"
                mock_notify.assert_called_once()

                call_args = mock_notify.call_args
                assert call_args[0][0] == message
                assert "reason" in call_args[0][1]

    def test_moderate_message_task_idempotency(self, db):
        user = baker.make(User)
        room = baker.make(Room)
        message = baker.make(Message, room=room, author=user, content="Safe", status=Message.Status.APPROVED)

        result = moderate_message_task(str(message.id))
        assert result["status"] == "skipped"
        assert "already" in result["reason"]
