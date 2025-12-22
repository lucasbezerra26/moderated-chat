import uuid
from unittest.mock import patch

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from app.asgi import application
from app.chat.models import Message


@pytest.fixture
def user_token(user):
    """Gera um token JWT para o usuário de teste."""
    return str(AccessToken.for_user(user))


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
class TestChatConsumer:
    """Testes de integração para o ChatConsumer."""

    async def test_consumer_rejects_unauthenticated_user(self, room):
        """Verifica que usuários não autenticados recebem close code 4001."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/")
        # Sem token na query string, o middleware define AnonymousUser

        connected, close_code = await communicator.connect()

        assert connected is False
        assert close_code == 4001
        await communicator.disconnect()

    async def test_consumer_rejects_invalid_room(self, user, user_token):
        """Verifica que sala inexistente resulta em close code 4004."""
        fake_room_id = uuid.uuid4()
        communicator = WebsocketCommunicator(application, f"ws/chat/{fake_room_id}/?token={user_token}")

        connected, close_code = await communicator.connect()

        assert connected is False
        assert close_code == 4004
        await communicator.disconnect()

    async def test_consumer_accepts_authenticated_user(self, user, room, user_token):
        """Verifica conexão bem-sucedida e mensagem connection_established."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        connected, _ = await communicator.connect()
        assert connected is True

        response = await communicator.receive_json_from()
        assert response["type"] == "connection_established"
        assert str(room.id) in response["message"]

        await communicator.disconnect()

    async def test_consumer_handles_empty_message(self, user, room, user_token):
        """Verifica resposta de erro para mensagem vazia."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        await communicator.connect()
        await communicator.receive_json_from()

        await communicator.send_json_to({"type": "chat_message", "message": ""})

        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "vazia" in response["message"].lower()

        await communicator.disconnect()

    async def test_consumer_handles_unknown_message_type(self, user, room, user_token):
        """Verifica resposta de erro para tipo de mensagem desconhecido."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        await communicator.connect()
        await communicator.receive_json_from()

        await communicator.send_json_to({"type": "unknown_type", "data": "test"})

        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "desconhecido" in response["message"].lower()

        await communicator.disconnect()

    @patch("app.moderation.tasks.moderate_message_task.delay")
    async def test_consumer_queues_message_and_triggers_moderation(self, mock_task, user, room, user_token):
        """Verifica message_queued e chamada do Celery (mockado)."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        await communicator.connect()
        await communicator.receive_json_from()

        test_content = "Mensagem de teste para moderação"
        await communicator.send_json_to({"type": "chat_message", "message": test_content})

        response = await communicator.receive_json_from()
        assert response["type"] == "message_queued"
        assert response["message"]["content"] == test_content
        assert response["message"]["status"] == "PENDING"

        mock_task.assert_called_once()

        message_exists = await database_sync_to_async(Message.objects.filter(content=test_content).exists)()
        assert message_exists is True

        await communicator.disconnect()

    async def test_consumer_receives_broadcast_on_approval(self, user, room, user_token):
        """Verifica recebimento de chat_message via channel layer."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        await communicator.connect()
        await communicator.receive_json_from()

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        await channel_layer.group_send(
            f"chat_{room.id}",
            {
                "type": "chat_message",
                "message": {
                    "id": "test-id",
                    "content": "Mensagem aprovada",
                    "status": "APPROVED",
                },
            },
        )

        response = await communicator.receive_json_from()
        assert response["type"] == "chat_message"
        assert response["message"]["content"] == "Mensagem aprovada"
        assert response["message"]["status"] == "APPROVED"

        await communicator.disconnect()

    async def test_consumer_receives_rejection_notification(self, user, room, user_token):
        """Verifica recebimento de message_rejected no canal do usuário."""
        communicator = WebsocketCommunicator(application, f"ws/chat/{room.id}/?token={user_token}")

        await communicator.connect()
        await communicator.receive_json_from()

        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        await channel_layer.group_send(
            f"user_{user.id}",
            {
                "type": "message_rejected",
                "message": {
                    "id": "test-id",
                    "content": "Mensagem rejeitada",
                    "reason": "content_violation",
                },
            },
        )

        response = await communicator.receive_json_from()
        assert response["type"] == "message_rejected"
        assert response["message"]["reason"] == "content_violation"

        await communicator.disconnect()
