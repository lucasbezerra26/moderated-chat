from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from jwt import ExpiredSignatureError, InvalidTokenError
from jwt import decode as jwt_decode

User = get_user_model()


@database_sync_to_async
def get_user(token_key: str):
    signing_key = settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY)
    algorithm = settings.SIMPLE_JWT.get("ALGORITHM", "HS256")
    user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")

    try:
        payload = jwt_decode(token_key, signing_key, algorithms=[algorithm])
        user_id = payload.get(user_id_claim)
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except (InvalidTokenError, ExpiredSignatureError, User.DoesNotExist):
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Middleware customizado para autenticar via token JWT na query string do WebSocket.
    Ex: ws://...?token=eyJhbGci...
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        scope["user"] = await get_user(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
