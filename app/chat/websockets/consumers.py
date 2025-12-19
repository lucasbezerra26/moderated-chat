from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from typing import Dict, Any

from app.chat.models import Room, Message
from app.chat.services import MessageService


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
        Requer autenticação.
        """
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        room_exists = await self._check_room_exists()
        if not room_exists:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        user_channel_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(
            user_channel_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Conectado à sala {self.room_id}'
        }))

    async def disconnect(self, close_code: int) -> None:
        """
        Desconecta usuário do WebSocket e remove do grupo.

        Args:
            close_code: Código de fechamento da conexão
        """
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        if hasattr(self, 'user') and self.user.is_authenticated:
            user_channel_name = f'user_{self.user.id}'
            await self.channel_layer.group_discard(
                user_channel_name,
                self.channel_name
            )

    async def receive(self, text_data: str) -> None:
        """
        Recebe mensagem do cliente, valida e envia para moderação.

        Args:
            text_data: Mensagem JSON do cliente
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self._handle_chat_message(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Tipo de mensagem desconhecido: {message_type}'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'JSON inválido'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Erro ao processar mensagem: {str(e)}'
            }))

    async def _handle_chat_message(self, data: Dict[str, Any]) -> None:
        """
        Processa mensagem de chat criando-a em estado PENDING.

        Args:
            data: Dados da mensagem do cliente
        """
        content = data.get('message', '').strip()

        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Mensagem vazia'
            }))
            return

        room = await self._get_room()
        message = await MessageService.create_message(
            room=room,
            author=self.user,
            content=content
        )

        await self.send(text_data=json.dumps({
            'type': 'message_queued',
            'message': {
                'id': str(message.id),
                'content': message.content,
                'status': message.status,
                'created_at': message.created_at.isoformat()
            }
        }))

    async def chat_message(self, event: Dict[str, Any]) -> None:
        """
        Handler para broadcast de mensagens aprovadas.
        Chamado pelo Celery via channel layer.

        Args:
            event: Evento com dados da mensagem
        """
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def message_rejected(self, event: Dict[str, Any]) -> None:
        """
        Handler para notificação de mensagem rejeitada.
        Chamado pelo Celery via channel layer.

        Args:
            event: Evento com dados da rejeição
        """
        await self.send(text_data=json.dumps({
            'type': 'message_rejected',
            'message': event['message']
        }))

    @database_sync_to_async
    def _check_room_exists(self) -> bool:
        """Verifica se a sala existe"""
        return Room.objects.filter(id=self.room_id).exists()

    @database_sync_to_async
    def _get_room(self) -> Room:
        """Obtém instância da sala"""
        return Room.objects.get(id=self.room_id)

