import structlog
from django.conf import settings

from app.moderation.domain.strategies import ModerationResult, ModerationStrategy
from app.moderation.infrastructure.gemini import GeminiModerator
from app.moderation.infrastructure.local import LocalDictionaryModerator

logger = structlog.get_logger(__name__)


class ModerationService:
    """
    Application Service: Orquestra estratégias de moderação.

    Responsabilidades:
    - Selecionar estratégia baseada em configuração
    - Implementar fallback entre provedores
    - Expor interface única para camada de tarefas (Celery)

    Esta camada NÃO conhece detalhes de implementação (APIs, arquivos).
    Apenas orquestra interfaces do Domain.
    """

    _STRATEGIES: dict[str, type[ModerationStrategy]] = {
        "gemini": GeminiModerator,
        "local": LocalDictionaryModerator,
    }

    @staticmethod
    def _get_strategy(provider: str) -> ModerationStrategy:
        strategy_class = ModerationService._STRATEGIES.get(provider)

        if not strategy_class:
            logger.warning(
                "unknown_provider_fallback",
                provider=provider,
                available=list(ModerationService._STRATEGIES.keys()),
            )
            strategy_class = LocalDictionaryModerator

        return strategy_class()

    @staticmethod
    def moderate(content: str) -> ModerationResult:
        """
        Analisa conteúdo usando o provedor configurado.

        Args:
            content: Conteúdo da mensagem a ser moderada

        Returns:
            ModerationResult contendo:
                - verdict: "APPROVED" ou "REJECTED"
                - provider: Nome do provedor de moderação
                - score: Score de confiança (0.0 a 1.0)
                - details: Detalhes adicionais incluindo motivo de rejeição

        Raises:
            Em caso de falha do provedor principal, usa fallback automático para LocalDictionaryModerator
        """
        provider = settings.MODERATION_PROVIDER.lower()
        log = logger.bind(provider=provider, content_length=len(content))

        try:
            strategy = ModerationService._get_strategy(provider)
            result = strategy.moderate(content)
            log.info("moderation_success", verdict=result["verdict"])
            return result

        except Exception as exc:
            log.warning("primary_strategy_failed_fallback", error=str(exc))

            try:
                fallback_strategy = LocalDictionaryModerator()
                result = fallback_strategy.moderate(content)
                log.info("fallback_success", verdict=result["verdict"])
                return result
            except Exception as fallback_exc:
                log.error("fallback_failed", error=str(fallback_exc))
                return ModerationResult(
                    verdict="REJECTED",
                    provider="system",
                    score=0.0,
                    details={"reason": "Todos os provedores falharam", "error": str(fallback_exc)},
                )
