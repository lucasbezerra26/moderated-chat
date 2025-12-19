import pytest
from django.contrib.auth.models import AnonymousUser
from model_bakery import baker

from app.accounts.models import User
from app.chat.models import Room


@pytest.fixture
def user(db):
    """Fixture que cria um usuário autenticado."""
    return baker.make(User, email="test@example.com", name="Test User")


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
