import structlog
from django.conf import settings

from app.moderation.domain.strategies import ModerationResult, ModerationStrategy

logger = structlog.get_logger(__name__)


class LocalDictionaryModerator(ModerationStrategy):
    """
    Implementação de moderação usando dicionário local de palavras bloqueadas.

    Camada de Infraestrutura: responsável por lógica de matching
    com lista de palavras proibidas configurada via settings.
    """

    def __init__(self):
        self.blocked_words = settings.PROFANITY_LIST

    def moderate(self, content: str) -> ModerationResult:
        content_lower = content.lower()

        for word in self.blocked_words:
            if word in content_lower:
                return ModerationResult(
                    verdict="REJECTED",
                    provider=self.get_provider_name(),
                    score=1.0,
                    details={"reason": f"Palavra proibida detectada: {word}"},
                )

        return ModerationResult(
            verdict="APPROVED",
            provider=self.get_provider_name(),
            score=1.0,
            details={"reason": "clean_content"},
        )

    def get_provider_name(self) -> str:
        return "local_dictionary"
