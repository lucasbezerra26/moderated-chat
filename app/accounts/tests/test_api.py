import pytest
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from app.accounts.models import User


@pytest.mark.integration
@pytest.mark.django_db
class TestUserViewSet:
    """Testes do UserViewSet."""

    def test_list_users_authenticated(self, authenticated_client: APIClient) -> None:
        baker.make(User, _quantity=3)

        response = authenticated_client.get("/api/auth/users/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 4

    def test_list_users_unauthenticated_fails(self, api_client: APIClient) -> None:
        response = api_client.get("/api/auth/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_user_authenticated(self, authenticated_client: APIClient, user: User) -> None:
        response = authenticated_client.get(f"/api/auth/users/{user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["name"] == user.name
