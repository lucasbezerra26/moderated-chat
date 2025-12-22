import structlog
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = structlog.get_logger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler de exceção customizado para DRF.
    Loga erros de forma estruturada e mantém resposta padrão do DRF.
    """
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code < 500:
            logger.warning(
                "api_client_error",
                status_code=response.status_code,
                method=context["request"].method,
                path=context["request"].path,
                details=response.data,
            )
        else:
            logger.error(
                "api_server_error",
                status_code=response.status_code,
                method=context["request"].method,
                path=context["request"].path,
                exc=str(exc),
            )
    else:
        logger.exception(
            "api_unhandled_exception", method=context["request"].method, path=context["request"].path, exc=str(exc)
        )
        return Response(
            {"detail": "Ocorreu um erro inesperado no servidor."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
