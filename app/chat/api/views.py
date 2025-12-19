from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from app.accounts.models import User
from app.chat.api.permissions import IsRoomAdmin, IsRoomParticipant
from app.chat.api.serializers import (
    AddParticipantSerializer,
    MessageSerializer,
    RoomCreateSerializer,
    RoomParticipantSerializer,
    RoomSerializer,
)
from app.chat.models import Message, Room
from app.chat.services import RoomService


class MessageCursorPagination(CursorPagination):
    """Paginação por cursor para mensagens (scroll infinito)."""

    page_size = 50
    ordering = "-created_at"
    cursor_query_param = "cursor"


@extend_schema_view(
    list=extend_schema(
        summary="Listar salas do usuário",
        responses={200: RoomSerializer(many=True)},
        tags=["Rooms"],
    ),
    create=extend_schema(
        summary="Criar nova sala",
        request=RoomCreateSerializer,
        responses={201: RoomSerializer},
        tags=["Rooms"],
    ),
    retrieve=extend_schema(
        summary="Detalhes da sala",
        responses={200: RoomSerializer},
        tags=["Rooms"],
    ),
)
class RoomViewSet(viewsets.ViewSet):
    """ViewSet para gerenciamento de salas."""

    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    lookup_field = "pk"
    pagination_class = MessageCursorPagination

    def get_queryset(self):
        return Room.objects.filter(participants=self.request.user)

    def list(self, request: Request) -> Response:
        """Lista salas do usuário autenticado."""
        queryset = self.get_queryset().prefetch_related("memberships")
        serializer = RoomSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request: Request) -> Response:
        """Cria uma nova sala com o usuário como ADMIN."""
        serializer = RoomCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from asgiref.sync import async_to_sync

        room = async_to_sync(RoomService.create_room)(
            name=serializer.validated_data["name"],
            creator=request.user,
            is_private=serializer.validated_data.get("is_private", False),
        )

        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk=None) -> Response:
        """Retorna detalhes de uma sala."""
        room = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(RoomSerializer(room).data)

    @extend_schema(
        summary="Adicionar participante à sala",
        request=AddParticipantSerializer,
        responses={201: RoomParticipantSerializer},
        tags=["Rooms"],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="participants",
        permission_classes=[IsAuthenticated, IsRoomParticipant, IsRoomAdmin],
    )
    def add_participant(self, request: Request, pk=None) -> Response:
        """Adiciona um participante à sala (apenas ADMIN em salas privadas)."""
        room = get_object_or_404(Room, pk=pk)
        self.check_object_permissions(request, room)

        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_user = get_object_or_404(User, pk=serializer.validated_data["user_id"])

        from asgiref.sync import async_to_sync

        participant = async_to_sync(RoomService.add_participant)(room=room, new_user=new_user, requester=request.user)

        return Response(
            RoomParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Remover participante da sala",
        tags=["Rooms"],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="participants/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsRoomParticipant, IsRoomAdmin],
    )
    def remove_participant(self, request: Request, pk=None, user_id=None) -> Response:
        """Remove um participante da sala (apenas ADMIN em salas privadas)."""
        room = get_object_or_404(Room, pk=pk)
        self.check_object_permissions(request, room)

        user_to_remove = get_object_or_404(User, pk=user_id)

        from asgiref.sync import async_to_sync

        async_to_sync(RoomService.remove_participant)(room=room, user_to_remove=user_to_remove, requester=request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Listar mensagens da sala",
        responses={200: MessageSerializer(many=True)},
        tags=["Messages"],
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="messages",
        permission_classes=[IsAuthenticated, IsRoomParticipant],
    )
    def messages(self, request: Request, pk=None) -> Response:
        """Lista mensagens aprovadas da sala com paginação por cursor."""
        room = get_object_or_404(Room, pk=pk)
        self.check_object_permissions(request, room)

        queryset = (
            Message.objects.filter(room=room, status=Message.Status.APPROVED)
            .select_related("author")
            .order_by("-created_at")
        )

        paginator = MessageCursorPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(queryset, many=True)
        return Response(serializer.data)
