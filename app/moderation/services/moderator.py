from abc import ABC, abstractmethod
from typing import Any, Dict

from django.conf import settings

from app.moderation.services.gemini import GeminiModerationService
from app.moderation.services.local import LocalModerationService


class ModerationStrategy(ABC):
    """
    Interface abstrata para estratégias de moderação.
    Garante que todos os provedores implementem o método moderate.
    """

    @abstractmethod
    def moderate(self, content: str) -> Dict[str, Any]:
        """
        Analisa conteúdo e retorna veredicto de moderação.

        Args:
            content: Conteúdo da mensagem a ser moderada

        Returns:
            Dict contendo verdict, provider, score e details
        """
        pass


class ModerationService:
    """
    Contexto do Strategy Pattern para moderação de mensagens.
    Delega a moderação para o provedor configurado via settings.
    """

    _STRATEGIES = {
        "gemini": GeminiModerationService,
        "local": LocalModerationService,
    }

    @staticmethod
    def _get_provider():
        """
        Retorna o provedor de moderação configurado.

        Returns:
            Instância do provedor configurado via settings.MODERATION_PROVIDER

        Raises:
            ValueError: Se o provedor configurado for inválido
        """
        provider_name = settings.MODERATION_PROVIDER

        strategy_class = ModerationService._STRATEGIES.get(provider_name)

        if not strategy_class:
            raise ValueError(
                f"Provedor de moderação inválido: {provider_name}. "
                f"Opções válidas: {list(ModerationService._STRATEGIES.keys())}"
            )

        return strategy_class()

    @staticmethod
    def moderate(content: str) -> Dict[str, Any]:
        """
        Analisa conteúdo usando o provedor configurado.

        Args:
            content: Conteúdo da mensagem a ser moderada

        Returns:
            Dict contendo:
                - verdict: "APPROVED" ou "REJECTED"
                - provider: Nome do provedor de moderação
                - score: Score de confiança (0.0 a 1.0)
                - details: Detalhes adicionais incluindo motivo de rejeição
        """
        provider = ModerationService._get_provider()
        return provider.moderate(content)
