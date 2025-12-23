from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.api.serializers import RegisterSerializer, UserSerializer
from app.accounts.models import User


class RegisterView(APIView):
    """View para registro de novos usuários."""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Registrar novo usuário",
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    list=extend_schema(
        summary="Listar usuários",
        description="Lista todos os usuários do sistema para permitir a adição de participantes em salas.",
    ),
    retrieve=extend_schema(
        summary="Detalhes do usuário",
    ),
)
class UserViewSet(ReadOnlyModelViewSet):
    """ViewSet para visualização de usuários."""

    queryset = User.objects.all().order_by("name")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
