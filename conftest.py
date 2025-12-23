import pytest
from django.contrib.auth.models import AnonymousUser
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import User
from app.chat.models import Room


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    """Fixture que cria um usuário autenticado."""
    return baker.make(User, email="test@example.com", name="Test User")


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
def room(db):
    """Fixture que cria uma sala de chat."""
    return baker.make(Room, name="Test Room", is_private=False)


@pytest.fixture
def anonymous_user():
    """Fixture que retorna um usuário anônimo."""
    return AnonymousUser()


@pytest.fixture(autouse=True)
def use_in_memory_channel_layer(settings):
    """Sobrescreve CHANNEL_LAYERS para usar InMemoryChannelLayer nos testes."""
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }


@pytest.fixture(autouse=True)
def mock_gemini_moderation(settings):
    """Mock do Google Gemini para testes quando o provider é gemini."""
    settings.MODERATION_PROVIDER = "local"
