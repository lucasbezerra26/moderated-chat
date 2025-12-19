import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import User
from app.chat.models import Message, Room, RoomParticipant


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def admin_user(db) -> User:
    return baker.make(User, email="admin@example.com", name="Admin User")


@pytest.fixture
def member_user(db) -> User:
    return baker.make(User, email="member@example.com", name="Member User")


@pytest.fixture
def room_with_admin(admin_user: User, db) -> Room:
    room = baker.make(Room, name="Test Room", is_private=False)
    baker.make(RoomParticipant, room=room, user=admin_user, role=RoomParticipant.Role.ADMIN)
    return room


@pytest.fixture
def private_room_with_admin(admin_user: User, db) -> Room:
    room = baker.make(Room, name="Private Room", is_private=True)
    baker.make(RoomParticipant, room=room, user=admin_user, role=RoomParticipant.Role.ADMIN)
    return room


@pytest.mark.integration
@pytest.mark.django_db
class TestRoomViewSet:
    """Testes do RoomViewSet."""

    def test_create_room_authenticated(self, authenticated_client: APIClient) -> None:
        response = authenticated_client.post(
            "/api/chat/rooms/",
            {"name": "Nova Sala", "is_private": False},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Nova Sala"
        assert response.data["is_private"] is False

    def test_create_room_unauthenticated_fails(self, api_client: APIClient) -> None:
        response = api_client.post(
            "/api/chat/rooms/",
            {"name": "Nova Sala", "is_private": False},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_rooms_only_user_rooms(self, admin_user: User, room_with_admin: Room, db) -> None:
        other_room = baker.make(Room, name="Other Room")

        client = APIClient()
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.get("/api/chat/rooms/")

        assert response.status_code == status.HTTP_200_OK
        room_ids = [r["id"] for r in response.data]
        assert str(room_with_admin.id) in room_ids
        assert str(other_room.id) not in room_ids

    def test_add_participant_as_admin(
        self, admin_user: User, member_user: User, private_room_with_admin: Room
    ) -> None:
        client = APIClient()
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.post(
            f"/api/chat/rooms/{private_room_with_admin.id}/participants/",
            {"user_id": str(member_user.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert RoomParticipant.objects.filter(room=private_room_with_admin, user=member_user).exists()

    def test_add_participant_as_member_fails(
        self, admin_user: User, member_user: User, private_room_with_admin: Room, db
    ) -> None:
        baker.make(
            RoomParticipant,
            room=private_room_with_admin,
            user=member_user,
            role=RoomParticipant.Role.MEMBER,
        )
        new_user = baker.make(User, email="new@example.com", name="New User")

        client = APIClient()
        refresh = RefreshToken.for_user(member_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.post(
            f"/api/chat/rooms/{private_room_with_admin.id}/participants/",
            {"user_id": str(new_user.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.integration
@pytest.mark.django_db
class TestMessageViewSet:
    """Testes do MessageViewSet (via action no RoomViewSet)."""

    def test_list_messages_only_approved(self, admin_user: User, room_with_admin: Room, db) -> None:
        approved = baker.make(
            Message, room=room_with_admin, author=admin_user, content="Approved", status=Message.Status.APPROVED
        )
        pending = baker.make(
            Message, room=room_with_admin, author=admin_user, content="Pending", status=Message.Status.PENDING
        )
        rejected = baker.make(
            Message, room=room_with_admin, author=admin_user, content="Rejected", status=Message.Status.REJECTED
        )

        client = APIClient()
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.get(f"/api/chat/rooms/{room_with_admin.id}/messages/")

        assert response.status_code == status.HTTP_200_OK
        message_ids = [m["id"] for m in response.data["results"]]
        assert str(approved.id) in message_ids
        assert str(pending.id) not in message_ids
        assert str(rejected.id) not in message_ids

    def test_list_messages_with_pagination(self, admin_user: User, room_with_admin: Room, db) -> None:
        for i in range(60):
            baker.make(
                Message,
                room=room_with_admin,
                author=admin_user,
                content=f"Message {i}",
                status=Message.Status.APPROVED,
            )

        client = APIClient()
        refresh = RefreshToken.for_user(admin_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.get(f"/api/chat/rooms/{room_with_admin.id}/messages/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 50
        assert response.data["next"] is not None

    def test_list_messages_not_participant_fails(self, member_user: User, room_with_admin: Room) -> None:
        client = APIClient()
        refresh = RefreshToken.for_user(member_user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        response = client.get(f"/api/chat/rooms/{room_with_admin.id}/messages/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
