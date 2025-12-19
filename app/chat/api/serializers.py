from rest_framework import serializers

from app.accounts.models import User
from app.chat.models import Message, Room, RoomParticipant


class AuthorSerializer(serializers.ModelSerializer):
    """Serializer para representação aninhada do autor."""

    class Meta:
        model = User
        fields = ["id", "name", "email"]
        read_only_fields = fields


class RoomSerializer(serializers.ModelSerializer):
    """Serializer para leitura de salas."""

    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ["id", "name", "is_private", "created_at", "participants_count"]
        read_only_fields = fields

    def get_participants_count(self, obj: Room) -> int:
        return obj.memberships.count()


class RoomCreateSerializer(serializers.Serializer):
    """Serializer para criação de salas."""

    name = serializers.CharField(max_length=255)
    is_private = serializers.BooleanField(default=False)


class RoomParticipantSerializer(serializers.ModelSerializer):
    """Serializer para participantes da sala."""

    user = AuthorSerializer(read_only=True)

    class Meta:
        model = RoomParticipant
        fields = ["user", "role", "created_at"]
        read_only_fields = fields


class AddParticipantSerializer(serializers.Serializer):
    """Serializer para adicionar participante."""

    user_id = serializers.UUIDField()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer para mensagens."""

    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "content", "status", "created_at", "author"]
        read_only_fields = fields
