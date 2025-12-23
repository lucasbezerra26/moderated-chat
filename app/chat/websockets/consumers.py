import json
from typing import Any, Dict

import structlog
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from app.chat.models import Room
from app.chat.services.message_service import MessageService

logger = structlog.get_logger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para chat em tempo real.

    Responsável por:
    - Conectar usuário à sala
    - Receber mensagens e disparar moderação
    - Broadcast de mensagens aprovadas
    - Notificações de rejeição
    """

    async def connect(self) -> None:
        """
        Conecta usuário ao WebSocket e adiciona ao grupo da sala.
        Requer autenticação e participação na sala.
        """
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        log = logger.bind(user_id=str(getattr(self.user, "id", "anon")), room_id=self.room_id)

        if not self.user.is_authenticated:
            log.warning("ws_connection_unauthenticated")
            await self.close(code=4001)
            return

        try:
            self.room = await self._get_room()
        except Room.DoesNotExist:
            log.warning("ws_connection_room_not_found")
            await self.close(code=4004)
            return

        is_allowed = await self._check_permission()
        if not is_allowed:
            log.warning("ws_connection_forbidden", reason="not_participant")
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        user_channel_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(user_channel_name, self.channel_name)

        await self.accept()
        log.info("ws_connected")

        await self.send(
            text_data=json.dumps({"type": "connection_established", "message": f"Conectado à sala {self.room_id}"})
        )

    async def disconnect(self, close_code: int) -> None:
        """
        Desconecta usuário do WebSocket e remove do grupo.

        Args:
            close_code: Código de fechamento da conexão
        """
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        if hasattr(self, "user") and self.user.is_authenticated:
            user_channel_name = f"user_{self.user.id}"
            await self.channel_layer.group_discard(user_channel_name, self.channel_name)

        logger.info("ws_disconnected", user_id=str(getattr(self.user, "id", "anon")), close_code=close_code)

    async def receive(self, text_data: str) -> None:
        """
        Recebe mensagem do cliente, valida e envia para moderação.

        Args:
            text_data: Mensagem JSON do cliente
        """
        log = logger.bind(user_id=str(self.user.id), room_id=self.room_id)
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "chat_message":
                is_participant = await self._is_user_participant()
                if not is_participant:
                    log.warning("ws_message_denied", reason="no_longer_participant")
                    await self.send(
                        text_data=json.dumps({"type": "error", "message": "Você não é mais participante desta sala"})
                    )
                    await self.close(code=4003)
                    return

                await self._handle_chat_message(data)
            else:
                log.warning("ws_unknown_message_type", type=message_type)
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": f"Tipo de mensagem desconhecido: {message_type}"}
                    )
                )

        except json.JSONDecodeError:
            log.warning("ws_invalid_json")
            await self.send(text_data=json.dumps({"type": "error", "message": "JSON inválido"}))
        except Exception as e:
            log.exception("ws_receive_error")
            await self.send(
                text_data=json.dumps({"type": "error", "message": f"Erro ao processar mensagem: {str(e)}"})
            )

    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        """
        Processa mensagem de chat criando-a em estado PENDING.

        Args:
            data: Dados da mensagem do cliente
        """
        content = data.get("message", "").strip()

        if not content:
            await self.send(text_data=json.dumps({"type": "error", "message": "Mensagem vazia"}))
            return

        room = await self._get_room()
        message = await MessageService.create_message(room=room, author=self.user, content=content)

        logger.info("ws_message_queued", message_id=str(message.id), user_id=str(self.user.id))

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_queued",
                    "message": {
                        "id": str(message.id),
                        "content": message.content,
                        "status": message.status,
                        "created_at": message.created_at.isoformat(),
                    },
                }
            )
        )

    async def chat_message(self, event: Dict[str, Any]) -> None:
        """
        Handler para broadcast de mensagens aprovadas.
        Chamado pelo Celery via channel layer.

        Args:
            event: Evento com dados da mensagem
        """
        await self.send(text_data=json.dumps({"type": "chat_message", "message": event["message"]}))

    async def message_rejected(self, event: Dict[str, Any]) -> None:
        """
        Handler para notificação de mensagem rejeitada.
        Chamado pelo Celery via channel layer.

        Args:
            event: Evento com dados da rejeição
        """
        await self.send(text_data=json.dumps({"type": "message_rejected", "message": event["message"]}))

    @database_sync_to_async
    def _get_room(self) -> Room:
        """Obtém instância da sala"""
        return Room.objects.get(id=self.room_id)

    @database_sync_to_async
    def _check_permission(self) -> bool:
        """
        Verifica se o usuário tem permissão para acessar a sala.

        Regras:
        - Sala pública: Qualquer usuário autenticado pode acessar
        - Sala privada: Apenas participantes (RoomParticipant) podem acessar

        Returns:
            bool: True se permitido, False caso contrário
        """
        from app.chat.models import RoomParticipant

        if not self.room.is_private:
            return True

        return RoomParticipant.objects.filter(room=self.room, user=self.user).exists()

    @database_sync_to_async
    def _is_user_participant(self) -> bool:
        """
        Verifica se o usuário ainda é participante da sala.
        Usado no receive para detectar se foi removido durante a conexão.

        Returns:
            bool: True se ainda é participante, False caso contrário
        """
        from app.chat.models import RoomParticipant

        if not self.room.is_private:
            return True

        return RoomParticipant.objects.filter(room=self.room, user=self.user).exists()
