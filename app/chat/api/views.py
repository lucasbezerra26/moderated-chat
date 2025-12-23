from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.accounts.models import User
from app.chat.api.pagination import MessageCursorPagination
from app.chat.api.permissions import IsRoomAdmin, IsRoomParticipant
from app.chat.api.serializers import (
    AddParticipantSerializer,
    MessageSerializer,
    RoomCreateSerializer,
    RoomDetailSerializer,
    RoomParticipantSerializer,
    RoomSerializer,
)
from app.chat.models import Message, Room
from app.chat.services.room_service import RoomService


@extend_schema_view(
    list=extend_schema(
        summary="Listar salas do usuário",
    ),
    create=extend_schema(
        summary="Criar nova sala",
    ),
    retrieve=extend_schema(
        summary="Detalhes da sala",
    ),
)
class RoomViewSet(ModelViewSet):
    """ViewSet para gerenciamento de salas."""

    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return (
            Room.objects.filter(Q(participants=self.request.user) | Q(is_private=False))
            .prefetch_related("memberships")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return RoomCreateSerializer
        if self.action == "retrieve":
            return RoomDetailSerializer
        return RoomSerializer

    def perform_create(self, serializer):
        room = RoomService.create_room(
            name=serializer.validated_data["name"],
            creator=self.request.user,
            is_private=serializer.validated_data.get("is_private", False),
        )
        serializer.instance = room

    @extend_schema(
        summary="Adicionar participante à sala",
        request=AddParticipantSerializer,
        responses={201: RoomParticipantSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="participants",
        permission_classes=[IsAuthenticated, IsRoomParticipant, IsRoomAdmin],
    )
    def add_participant(self, request: Request, pk=None) -> Response:
        """Adiciona um participante à sala (apenas ADMIN em salas privadas)."""
        room = self.get_object()

        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(pk=serializer.validated_data["user_id"]).first()
        if not user:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        participant = RoomService.add_participant(room=room, new_user=user, requester=request.user)

        return Response(
            RoomParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Remover participante da sala",
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path="participants/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsRoomParticipant, IsRoomAdmin],
    )
    def remove_participant(self, request: Request, pk=None, user_id=None) -> Response:
        """Remove um participante da sala (apenas ADMIN em salas privadas)."""
        room = self.get_object()

        user_to_remove = User.objects.filter(pk=user_id).first()
        if not user_to_remove:
            return Response(
                {"detail": "Usuário não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        RoomService.remove_participant(room=room, user_to_remove=user_to_remove, requester=request.user)

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
        """Lista mensagens da sala com paginação por cursor.

        Retorna:
        - Todas as mensagens com status APPROVED.
        - Mensagens do próprio usuário (mesmo se PENDING ou REJECTED).
        """
        room = self.get_object()

        queryset = (
            Message.objects.filter(Q(room=room), Q(status=Message.Status.APPROVED) | Q(author=request.user))
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
