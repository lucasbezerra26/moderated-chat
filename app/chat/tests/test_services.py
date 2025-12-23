from unittest.mock import MagicMock, patch

import pytest
from model_bakery import baker

from app.accounts.models import User
from app.chat.models import Message, Room
from app.chat.services.broadcast_service import BroadcastService


@pytest.mark.unit
@pytest.mark.django_db
class TestBroadcastService:
    """Testes para o BroadcastService."""

    def test_broadcast_message_to_room_calls_channel_layer(self):
        """Verifica que broadcast_message_to_room chama o channel_layer corretamente."""
        mock_channel_layer = MagicMock()
        mock_group_send = MagicMock()

        with (
            patch("app.chat.services.broadcast_service.get_channel_layer", return_value=mock_channel_layer),
            patch("app.chat.services.broadcast_service.async_to_sync", return_value=mock_group_send),
        ):
            user = baker.make(User, name="Test User", email="test@example.com")
            room = baker.make(Room, name="Test Room")
            message = baker.make(
                Message, room=room, author=user, content="Test message", status=Message.Status.APPROVED
            )

            BroadcastService.broadcast_message_to_room(message)

            mock_group_send.assert_called_once()
            call_args = mock_group_send.call_args
            group_name, payload = call_args[0]

            assert group_name == f"chat_{room.id}"
            assert payload["type"] == "chat_message"
            assert payload["message"]["content"] == "Test message"
            assert payload["message"]["status"] == Message.Status.APPROVED
            assert payload["message"]["author"]["id"] == str(user.id)

    def test_notify_author_rejection_calls_channel_layer(self):
        """Verifica que notify_author_rejection envia para o canal do usuário."""
        mock_channel_layer = MagicMock()
        mock_group_send = MagicMock()

        with (
            patch("app.chat.services.broadcast_service.get_channel_layer", return_value=mock_channel_layer),
            patch("app.chat.services.broadcast_service.async_to_sync", return_value=mock_group_send),
        ):
            user = baker.make(User, name="Test User", email="test@example.com")
            room = baker.make(Room, name="Test Room")
            message = baker.make(
                Message, room=room, author=user, content="Bad message", status=Message.Status.REJECTED
            )
            details = {"reason": "offensive_content"}

            BroadcastService.notify_author_rejection(message, details)

            mock_group_send.assert_called_once()
            call_args = mock_group_send.call_args
            group_name, payload = call_args[0]

            assert group_name == f"user_{user.id}"
            assert payload["type"] == "message_rejected"
            assert payload["message"]["content"] == "Bad message"
            assert payload["message"]["reason"] == "offensive_content"

    def test_notify_author_rejection_uses_default_reason(self):
        """Verifica que notify_author_rejection usa reason padrão quando não fornecido."""
        mock_channel_layer = MagicMock()
        mock_group_send = MagicMock()

        with (
            patch("app.chat.services.broadcast_service.get_channel_layer", return_value=mock_channel_layer),
            patch("app.chat.services.broadcast_service.async_to_sync", return_value=mock_group_send),
        ):
            user = baker.make(User, name="Test User", email="test@example.com")
            room = baker.make(Room, name="Test Room")
            message = baker.make(
                Message, room=room, author=user, content="Bad message", status=Message.Status.REJECTED
            )

            BroadcastService.notify_author_rejection(message, {})

            call_args = mock_group_send.call_args
            _, payload = call_args[0]

            assert payload["message"]["reason"] == "content_violation"
